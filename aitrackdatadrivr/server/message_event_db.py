"""Normalização e persistência idempotente de callbacks de mensagem."""

from datetime import datetime, timezone
import hashlib
import json

from .action_queue_db import transition_action
from .monitor_db import get_connection

STATUS_MAP = {
    'accepted': 'accepted', 'queued': 'accepted',
    'sent': 'sent', 'submitted': 'sent',
    'delivered': 'delivered',
    'read': 'read', 'seen': 'read',
    'responded': 'responded', 'replied': 'responded',
    'failed': 'failed', 'undelivered': 'failed', 'rejected': 'failed',
}
ALLOWED_METADATA = {'error_code', 'reply_category', 'channel', 'sandbox'}


def normalize_status(value):
    return STATUS_MAP.get(str(value or '').strip().lower(), 'unknown')


def parse_provider_timestamp(value):
    if value in (None, ''):
        return None
    if not isinstance(value, str):
        raise ValueError('occurred_at deve ser ISO-8601')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('occurred_at inválido') from exc
    if parsed.tzinfo is None:
        raise ValueError('occurred_at exige fuso')
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def sanitize_metadata(payload):
    return {key: payload[key] for key in ALLOWED_METADATA if key in payload}


def _serialize(row, replay):
    result = dict(row)
    if isinstance(result.get('sanitized_metadata_json'), str):
        result['metadata'] = json.loads(result.pop('sanitized_metadata_json'))
    for field in ('provider_occurred_at', 'received_at'):
        if isinstance(result.get(field), datetime):
            result[field] = result[field].isoformat()
    result['idempotent_replay'] = replay
    return result


def record_message_event(payload):
    provider = str(payload.get('provider_code') or '').strip()
    message_id = str(payload.get('provider_message_id') or '').strip()
    event_id = str(payload.get('provider_event_id') or '').strip()
    provider_status = str(payload.get('status') or '').strip().lower()
    if not provider or not message_id or not event_id or not provider_status:
        raise ValueError('provider_code, provider_message_id, provider_event_id e status obrigatórios')
    if max(map(len, (provider, message_id, event_id))) > 150 or len(provider_status) > 100:
        raise ValueError('identificador de callback acima do limite')
    normalized = normalize_status(provider_status)
    occurred_at = parse_provider_timestamp(payload.get('occurred_at'))
    canonical = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    metadata = sanitize_metadata(payload)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.message_provider_events "
            "WHERE provider_code=%s AND provider_event_id=%s FOR UPDATE",
            (provider, event_id),
        )
        existing = cursor.fetchone()
        if existing:
            if existing['payload_sha256'] != digest:
                raise ValueError('provider_event_id reutilizado com payload divergente')
            conn.commit()
            return _serialize(existing, True)
        cursor.execute(
            """SELECT r.id receipt_id,r.action_id,a.public_id,a.status,a.version,
                      a.idempotency_key
               FROM monitoramento.message_dispatch_receipts r
               JOIN monitoramento.action_queue a ON a.id=r.action_id
              WHERE r.provider_code=%s AND r.provider_message_id=%s FOR UPDATE""",
            (provider, message_id),
        )
        linked = cursor.fetchone()
        if not linked:
            raise LookupError('Recibo da mensagem não encontrado')
        cursor.execute(
            """INSERT INTO monitoramento.message_provider_events
               (action_id,receipt_id,provider_code,provider_event_id,
                normalized_status,provider_status,provider_occurred_at,
                payload_sha256,sanitized_metadata_json)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                linked['action_id'], linked['receipt_id'], provider, event_id,
                normalized, provider_status, occurred_at, digest,
                json.dumps(metadata, separators=(',', ':'), sort_keys=True),
            ),
        )
        event_pk = cursor.lastrowid
        command = None
        if normalized in {'delivered', 'read'} and linked['status'] == 'sent':
            command = 'mark_delivered'
        elif normalized == 'responded' and linked['status'] in {'sent', 'delivered'}:
            command = 'mark_responded'
        elif normalized == 'failed' and linked['status'] in {'sent', 'delivered'}:
            command = 'fail'
        if command:
            transition_payload = {
                'expected_version': linked['version'],
                'idempotency_key': f'{linked["idempotency_key"]}:provider:{event_id}',
                'actor_type': 'provider', 'actor_id': provider,
            }
            if command == 'fail':
                transition_payload.update(
                    error_code=str(metadata.get('error_code') or 'PROVIDER_FAILED')[:100],
                    error_message='Falha reportada pelo provedor',
                )
            transition_action(
                linked['public_id'], command, transition_payload, connection=conn
            )
        cursor.execute(
            "SELECT * FROM monitoramento.message_provider_events WHERE id=%s",
            (event_pk,),
        )
        result = _serialize(cursor.fetchone(), False)
        conn.commit()
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
