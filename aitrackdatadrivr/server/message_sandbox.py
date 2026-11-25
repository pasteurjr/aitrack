"""Envio de mensagens restrito a sandbox, com recibo persistente e idempotente."""

import hashlib
import json
import os
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .action_queue_db import transition_action
from .monitor_db import get_connection
from .action_contact_policy import enforce_contact_policy
from .action_retry_db import settle_action_failure
from .contact_escalation_db import enforce_contact_consent

class MessageSandboxError(RuntimeError):
    def __init__(self, message, code='MESSAGE_SANDBOX_ERROR'):
        super().__init__(message); self.code=code

@dataclass(frozen=True)
class MessageReceipt:
    provider_code: str
    provider_message_id: str
    destination_hash: str
    request_sha256: str
    http_status: int
    response: dict

class SandboxMessageProvider:
    provider_code = 'http-sandbox'

    def __init__(self, endpoint: str, token: str, allowed_destinations: set[str], opener=urlopen):
        parsed = urlparse(endpoint)
        if not token:
            raise MessageSandboxError('MESSAGE_SANDBOX_TOKEN ausente')
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            raise MessageSandboxError('Endpoint sandbox inválido')
        if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost'}:
            raise MessageSandboxError('HTTP só é aceito em loopback')
        if parsed.scheme == 'https' and not any(
            marker in parsed.hostname.lower() for marker in ('sandbox', 'test')
        ):
            raise MessageSandboxError('Endpoint HTTPS deve identificar ambiente sandbox/test')
        if not allowed_destinations:
            raise MessageSandboxError('Allowlist sandbox vazia')
        if any(not value.upper().startswith(('TEST-', 'SANDBOX-')) for value in allowed_destinations):
            raise MessageSandboxError('Allowlist aceita somente identificadores TEST-/SANDBOX-')
        self.endpoint = endpoint
        self.token = token
        self.allowed = allowed_destinations
        self.opener = opener

    def send(self, destination: str, body: str, correlation_id: str) -> MessageReceipt:
        if destination not in self.allowed:
            raise MessageSandboxError('Destino fora da allowlist sandbox')
        if not isinstance(body, str) or not body.strip() or len(body) > 5000:
            raise MessageSandboxError('Mensagem vazia ou acima de 5000 caracteres')
        if not isinstance(correlation_id, str) or not correlation_id.strip() or len(correlation_id) > 100:
            raise MessageSandboxError('correlation_id inválido')
        payload = {
            'to': destination,
            'body': body,
            'correlation_id': correlation_id,
            'sandbox': True,
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(',', ':'), sort_keys=True
        ).encode()
        request = Request(
            self.endpoint,
            data=encoded,
            headers={
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Idempotency-Key': correlation_id,
                'X-AITrack-Environment': 'sandbox',
            },
            method='POST',
        )
        try:
            with self.opener(request,timeout=10) as response:
                status = response.status
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise MessageSandboxError('Resposta sandbox acima de 64 KiB')
                value = json.loads(raw.decode())
        except MessageSandboxError:
            raise
        except TimeoutError as exc:
            raise MessageSandboxError('Timeout no provedor sandbox','PROVIDER_TIMEOUT') from exc
        except Exception as exc:
            raise MessageSandboxError('Falha no provedor sandbox','PROVIDER_UNAVAILABLE') from exc
        message_id = str(value.get('message_id') or '').strip()
        if status not in range(200, 300) or not message_id or value.get('sandbox') is not True:
            raise MessageSandboxError('Recibo sandbox inválido')
        sanitized = {
            'message_id': message_id,
            'status': value.get('status', 'accepted'),
            'sandbox': True,
        }
        return MessageReceipt(
            self.provider_code,
            message_id,
            hashlib.sha256(destination.encode()).hexdigest(),
            hashlib.sha256(encoded).hexdigest(),
            status,
            sanitized,
        )


def _receipt_result(row, idempotent_replay):
    result = dict(row)
    if isinstance(result.get('response_json'), str):
        result['response'] = json.loads(result.pop('response_json'))
    result['idempotent_replay'] = idempotent_replay
    return result


def dispatch_message_action(public_id: str, provider: SandboxMessageProvider):
    """Consome uma ação `send_message` uma única vez e grava o recibo.

    O bloqueio da ação e a restrição única por ``action_id`` impedem dois workers
    de enviarem a mesma ação simultaneamente. O provedor também recebe o
    ``correlation_id`` estável para deduplicação no limite externo.
    """
    if not str(public_id).strip():
        raise ValueError('public_id obrigatório')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.action_queue WHERE public_id=%s FOR UPDATE",
            (public_id,),
        )
        action = cursor.fetchone()
        if not action:
            raise LookupError('Ação não encontrada')
        cursor.execute(
            "SELECT * FROM monitoramento.message_dispatch_receipts WHERE action_id=%s",
            (action['id'],),
        )
        existing = cursor.fetchone()
        if existing:
            conn.commit()
            return _receipt_result(existing, True)
        if action['action_type'] != 'send_message':
            raise ValueError('Ação não é do tipo send_message')
        if action['status'] not in {'pending', 'approved'}:
            raise ValueError(f'Ação não pode ser enviada em {action["status"]}')

        body = json.loads(action['payload_json']).get('body', '')
        action_payload = json.loads(action['payload_json'])
        enforce_contact_consent(conn,action['target_ref'])
        policy_decision = enforce_contact_policy(
            conn, action, 'message', action_payload.get('estimated_cost_cents', 0)
        )
        if not policy_decision['allowed']:
            conn.commit()
            raise MessageSandboxError(
                'Contato bloqueado pela política: ' + ','.join(policy_decision['denial_codes'])
            )
        claim = transition_action(
            public_id,
            'claim',
            {
                'expected_version': action['version'],
                'idempotency_key': f'{action["idempotency_key"]}:sandbox:claim',
                'actor_type': 'system',
                'actor_id': 'message-sandbox',
                'worker_id': 'message-sandbox',
                'lease_seconds': 30,
            },
            connection=conn,
        )
        try:
            # O public_id identifica unicamente a operação no provedor, inclusive
            # se o processo cair depois de o sandbox aceitar a requisição.
            receipt = provider.send(action['target_ref'], body, action['public_id'])
        except MessageSandboxError as exc:
            claimed_action={**action,'status':'claimed','version':claim['version'],
                            'attempt_count':claim['attempt_count']}
            settle_action_failure(
                claimed_action,exc.code,str(exc),'sandbox-send',conn,
            )
            conn.commit()
            raise
        cursor.execute(
            """INSERT INTO monitoramento.message_dispatch_receipts
               (action_id,provider_code,provider_message_id,destination_hash,
                request_sha256,http_status,response_json)
               VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (
                action['id'], receipt.provider_code, receipt.provider_message_id,
                receipt.destination_hash, receipt.request_sha256,
                receipt.http_status,
                json.dumps(receipt.response, separators=(',', ':'), sort_keys=True),
            ),
        )
        transition_action(
            public_id,
            'mark_sent',
            {
                'expected_version': claim['version'],
                'idempotency_key': f'{action["idempotency_key"]}:sandbox:sent',
                'actor_type': 'provider',
                'actor_id': provider.provider_code,
            },
            connection=conn,
        )
        cursor.execute(
            "SELECT * FROM monitoramento.message_dispatch_receipts WHERE action_id=%s",
            (action['id'],),
        )
        result = _receipt_result(cursor.fetchone(), False)
        conn.commit()
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def provider_from_environment(environ=os.environ):
    allowed = {
        value.strip()
        for value in environ.get('MESSAGE_SANDBOX_DESTINATIONS', '').split(',')
        if value.strip()
    }
    return SandboxMessageProvider(
        environ.get('MESSAGE_SANDBOX_URL', ''),
        environ.get('MESSAGE_SANDBOX_TOKEN', ''),
        allowed,
    )
