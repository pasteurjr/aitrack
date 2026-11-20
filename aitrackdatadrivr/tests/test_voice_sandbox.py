import json,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import pytest
from server.voice_sandbox import SandboxVoiceProvider,VoiceSandboxError,validate_automation_disclosure

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'051_create_voice_sandbox_receipts.sql'

class Handler(BaseHTTPRequestHandler):
    received=None
    def do_POST(self):
        Handler.received={'auth':self.headers.get('Authorization'),'key':self.headers.get('Idempotency-Key'),'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))}
        raw=json.dumps({'call_id':'voice-test-1','status':'accepted','sandbox':True}).encode();self.send_response(202);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,*_args):pass


def test_local_voice_sandbox_requires_disclosure_and_returns_sanitized_receipt():
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.handle_request);thread.start()
    provider=SandboxVoiceProvider(f'http://127.0.0.1:{server.server_port}/calls','secret',{'TEST-OWNER'})
    receipt=provider.call('TEST-OWNER','Olá, sou um assistente virtual automatizado do monitoramento.','action-1');thread.join(2);server.server_close()
    assert receipt.http_status==202 and receipt.provider_call_id=='voice-test-1'
    assert Handler.received['key']=='action-1' and Handler.received['body']['automation_disclosed'] is True
    assert 'TEST-OWNER' not in json.dumps(receipt.__dict__) and 'secret' not in json.dumps(receipt.__dict__)


def test_voice_fails_closed_outside_sandbox_allowlist_or_without_disclosure():
    with pytest.raises(VoiceSandboxError,match='automação'):validate_automation_disclosure('Olá, aqui é a central.')
    with pytest.raises(VoiceSandboxError,match='sandbox/test'):SandboxVoiceProvider('https://voice.example/calls','x',{'TEST-OWNER'})
    with pytest.raises(VoiceSandboxError,match='TEST-/SANDBOX-'):SandboxVoiceProvider('https://sandbox.example/calls','x',{'REAL-OWNER'})


def test_voice_receipt_is_versioned_sanitized_and_immutable():
    sql=MIGRATION.read_text().lower()
    for token in ('voice_dispatch_receipts','script_version_id','script_sha256','destination_hash','automation_disclosed','uq_voice_receipt_action'):
        assert token in sql
    assert 'voice receipt is immutable' in sql and 'voice receipts cannot be deleted' in sql
