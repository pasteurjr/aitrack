"""Escrita e consulta da auditoria transversal com redação de dados sensíveis."""

from datetime import date, datetime
import json
from uuid import uuid4

from .monitor_db import get_connection


SENSITIVE_KEYS = {
    'password', 'password_hash', 'token', 'access_token', 'refresh_token',
    'authorization', 'cookie', 'csrf', 'csrf_token', 'phone', 'telefone',
    'email', 'audio', 'transcript', 'prompt', 'api_key', 'secret',
}


def redact(value):
    if isinstance(value, dict):
        return {
            str(key): '[REDACTED]' if str(key).casefold() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _json(value):
    return None if value is None else json.dumps(
        redact(value), ensure_ascii=False, separators=(',', ':'), default=str,
    )


def record_event(event, connection=None):
    """Grava usando a conexão recebida para participar da transação de domínio."""
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO monitoramento.audit_events(
              public_id,tenant_id,actor_type,actor_user_id,actor_public_id,
              actor_display,action,resource_type,resource_public_id,before_json,
              after_json,reason,correlation_id,causation_id,request_id,
              source_ip_sha256,user_agent,metadata_json)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid4()), event['tenant_id'], event.get('actor_type', 'system'),
            event.get('actor_user_id'), event.get('actor_public_id'),
            event.get('actor_display'), event['action'], event['resource_type'],
            event.get('resource_public_id'), _json(event.get('before')),
            _json(event.get('after')), event.get('reason'),
            event.get('correlation_id'), event.get('causation_id'),
            event.get('request_id'), event.get('source_ip_sha256'),
            str(event.get('user_agent') or '')[:300] or None,
            _json(event.get('metadata') or {}),
        ))
        if owns:
            conn.commit()
        return cursor.lastrowid
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def list_events(tenant_id, filters, limit=100, cursor_id=None):
    clauses, params = ['tenant_id=%s'], [tenant_id]
    for field in ('actor_public_id', 'action', 'resource_type', 'correlation_id'):
        if filters.get(field):
            clauses.append(f'{field}=%s')
            params.append(filters[field])
    if filters.get('from'):
        clauses.append('occurred_at >= %s'); params.append(filters['from'])
    if filters.get('to'):
        clauses.append('occurred_at <= %s'); params.append(filters['to'])
    if cursor_id:
        clauses.append('id < %s'); params.append(cursor_id)
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT * FROM monitoramento.audit_events WHERE '
            + ' AND '.join(clauses) + ' ORDER BY id DESC LIMIT %s',
            tuple([*params, limit + 1]),
        )
        rows = cursor.fetchall(); has_more = len(rows) > limit; rows = rows[:limit]
        result = []
        for row in rows:
            item = dict(row)
            for field in ('before_json', 'after_json', 'metadata_json'):
                raw = item.pop(field)
                item[field[:-5]] = json.loads(raw) if raw else None
            if item.get('occurred_at'):
                item['occurred_at'] = item['occurred_at'].isoformat()
            result.append(item)
        return result, (rows[-1]['id'] if has_more and rows else None)
    finally:
        cursor.close(); conn.close()
