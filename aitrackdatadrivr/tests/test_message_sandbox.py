import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import pytest
from server.message_sandbox import (
    MessageSandboxError,
    SandboxMessageProvider,
    provider_from_environment,
)

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'045_create_message_sandbox_receipts.sql'
class Handler(BaseHTTPRequestHandler):
    received=None
    def do_POST(self):
        Handler.received={
            'auth': self.headers.get('Authorization'),
            'idempotency': self.headers.get('Idempotency-Key'),
            'environment': self.headers.get('X-AITrack-Environment'),
            'body':json.loads(self.rfile.read(int(self.headers['Content-Length']))),
        }
        data=json.dumps({'message_id':'sandbox-msg-1','status':'accepted','sandbox':True}).encode();self.send_response(202);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,*_args):pass

def test_real_local_sandbox_receipt_and_allowlist():
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.handle_request);thread.start()
    provider=SandboxMessageProvider(f'http://127.0.0.1:{server.server_port}/messages','secret',{'TEST-OWNER'})
    receipt=provider.send('TEST-OWNER','Mensagem de teste.','corr-1');thread.join(2);server.server_close()
    assert receipt.http_status==202 and receipt.provider_message_id=='sandbox-msg-1'
    assert Handler.received['auth']=='Bearer secret' and Handler.received['body']['sandbox'] is True
    assert Handler.received['idempotency']=='corr-1'
    assert Handler.received['environment']=='sandbox'
    assert 'TEST-OWNER' not in json.dumps(receipt.__dict__)
    with pytest.raises(MessageSandboxError,match='allowlist'):provider.send('REAL-OWNER','x','c')

def test_configuration_fails_closed_and_migration_is_immutable():
    with pytest.raises(MessageSandboxError):SandboxMessageProvider('http://example.com','x',{'TEST'})
    with pytest.raises(MessageSandboxError):SandboxMessageProvider('https://sandbox.example','',{'TEST'})
    with pytest.raises(MessageSandboxError, match='sandbox/test'):
        SandboxMessageProvider('https://api.example/messages','x',{'TEST-OWNER'})
    with pytest.raises(MessageSandboxError, match='TEST-/SANDBOX-'):
        SandboxMessageProvider('https://sandbox.example/messages','x',{'REAL-OWNER'})
    sql=MIGRATION.read_text().lower();assert 'message_dispatch_receipts' in sql and 'destination_hash' in sql
    assert 'trg_message_receipt_update' in sql and 'trg_message_receipt_delete' in sql and 'delete from' not in sql


def test_environment_requires_explicit_sandbox_configuration():
    provider = provider_from_environment({
        'MESSAGE_SANDBOX_URL': 'https://sandbox.example/messages',
        'MESSAGE_SANDBOX_TOKEN': 'test-token',
        'MESSAGE_SANDBOX_DESTINATIONS': 'TEST-OWNER-1, SANDBOX-OWNER-2',
    })
    assert provider.allowed == {'TEST-OWNER-1', 'SANDBOX-OWNER-2'}
    with pytest.raises(MessageSandboxError, match='TOKEN'):
        provider_from_environment({
            'MESSAGE_SANDBOX_URL': 'https://sandbox.example/messages',
            'MESSAGE_SANDBOX_DESTINATIONS': 'TEST-OWNER-1',
        })


def test_migration_enforces_one_receipt_per_action_and_sanitized_payload():
    sql = MIGRATION.read_text().lower()
    assert 'uq_message_receipt_action' in sql
    assert 'uq_message_receipt_provider' in sql
    assert 'response_json' in sql and 'destination_hash' in sql
    assert 'destination varchar' not in sql and 'body text' not in sql


def test_message_and_correlation_limits_fail_before_network():
    provider = SandboxMessageProvider(
        'https://sandbox.example/messages', 'x', {'TEST-OWNER'},
        opener=lambda *_args, **_kwargs: pytest.fail('rede não deveria ser chamada'),
    )
    with pytest.raises(MessageSandboxError, match='5000'):
        provider.send('TEST-OWNER', 'x' * 5001, 'corr-1')
    with pytest.raises(MessageSandboxError, match='correlation_id'):
        provider.send('TEST-OWNER', 'mensagem', '')
