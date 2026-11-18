"""Contrato persistente de comandos; nenhum transporte físico é presumido."""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from .monitor_db import get_connection


FINAL_STATUSES = {'acknowledged', 'nacked', 'timed_out', 'cancelled', 'failed'}
TRANSITIONS = {
    'requested': {'queued', 'cancelled', 'failed', 'timed_out'},
    'queued': {'sent', 'cancelled', 'failed', 'timed_out'},
    'sent': {'acknowledged', 'nacked', 'timed_out', 'failed'},
}
logger = logging.getLogger(__name__)


class CommandError(ValueError):
    code = 'INVALID_COMMAND'


class CommandUnsupported(CommandError):
    code = 'COMMAND_CAPABILITY_NOT_CONFIRMED'


class CommandNotFound(CommandError):
    code = 'COMMAND_NOT_FOUND'


class CommandConflict(CommandError):
    code = 'COMMAND_VERSION_CONFLICT'


def plan_transition(current: str, target: str) -> Dict:
    if current in FINAL_STATUSES:
        raise CommandError(f'Comando já finalizado como {current}')
    if target not in TRANSITIONS.get(current, set()):
        raise CommandError(f'Transição inválida: {current} → {target}')
    return {'from_status': current, 'to_status': target, 'final': target in FINAL_STATUSES}


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize(row: Dict, events=None, idempotent=False) -> Dict:
    result = dict(row)
    result['payload'] = json.loads(result.pop('payload_json'))
    for field in ('requested_at', 'sent_at', 'finalized_at', 'timeout_at'):
        result[field] = _iso(result.get(field))
    result['events'] = events or []
    result['idempotent'] = idempotent
    return result


def _events(cursor, command_id: int):
    cursor.execute(
        "SELECT id,from_status,to_status,actor_type,actor_id,event_code,message,"
        "provider_message_id,correlation_id,payload_json,occurred_at "
        "FROM monitoramento.device_command_events WHERE command_id=%s "
        "ORDER BY occurred_at,id",
        (command_id,),
    )
    rows = cursor.fetchall()
    for row in rows:
        row['payload'] = json.loads(row.pop('payload_json')) if row.get('payload_json') else None
        row['occurred_at'] = _iso(row['occurred_at'])
    return rows


def _confirmed_command(cursor, vehicle_id: int, capability_code: str):
    cursor.execute(
        "SELECT DISTINCT s.source_code,s.protocol_code,i.capability_code "
        "FROM monitoramento.sensors s "
        "JOIN monitoramento.capability_profiles p ON p.protocol_code=s.protocol_code "
        "AND (p.device_model=s.device_model OR p.device_model='*') AND p.status='active' "
        "JOIN monitoramento.capability_profile_items i ON i.profile_id=p.id "
        "WHERE s.vehicle_id=%s AND i.capability_type='command' "
        "AND i.capability_code=%s AND i.support_status='confirmed' "
        "AND NOT EXISTS (SELECT 1 FROM monitoramento.capability_profiles newer "
        "WHERE newer.protocol_code=p.protocol_code AND newer.device_model=p.device_model "
        "AND newer.status='active' AND newer.version_number>p.version_number) "
        "ORDER BY CASE WHEN p.device_model=s.device_model THEN 0 ELSE 1 END LIMIT 1",
        (vehicle_id, capability_code),
    )
    return cursor.fetchone()


def list_commands(vehicle_id: int, limit: int = 50) -> list:
    if not 1 <= limit <= 200:
        raise CommandError('limit deve estar entre 1 e 200')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM monitoramento.device_commands WHERE vehicle_id=%s "
            "ORDER BY requested_at DESC,id DESC LIMIT %s",
            (vehicle_id, limit),
        )
        commands = cursor.fetchall()
        return [_serialize(row, _events(cursor, row['id'])) for row in commands]
    finally:
        cursor.close()
        conn.close()


def create_command(vehicle_id: int, payload: Dict) -> Dict:
    capability = str(payload.get('capability_code') or '').strip()
    idempotency = str(payload.get('idempotency_key') or '').strip()
    correlation = str(payload.get('correlation_id') or '').strip()
    actor = payload.get('actor') if isinstance(payload.get('actor'), dict) else {}
    reason = str(payload.get('reason') or '').strip()
    command_payload = payload.get('payload')
    timeout_seconds = int(payload.get('timeout_seconds') or 30)
    if not capability or not idempotency or not correlation:
        raise CommandError('capability_code, idempotency_key e correlation_id são obrigatórios')
    if actor.get('type') not in {'human', 'system', 'agent'} or not actor.get('id') or not actor.get('name'):
        raise CommandError('actor completo é obrigatório')
    if len(reason) < 5 or not isinstance(command_payload, dict):
        raise CommandError('reason (mín. 5) e payload objeto são obrigatórios')
    if not 5 <= timeout_seconds <= 300:
        raise CommandError('timeout_seconds deve estar entre 5 e 300')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.device_commands "
            "WHERE source_code='tracker' AND idempotency_key=%s FOR UPDATE",
            (idempotency,),
        )
        existing = cursor.fetchone()
        if existing:
            if int(existing['vehicle_id']) != vehicle_id or existing['capability_code'] != capability:
                raise CommandConflict('idempotency_key já usada para outro comando')
            conn.commit()
            return _serialize(existing, _events(cursor, existing['id']), idempotent=True)
        supported = _confirmed_command(cursor, vehicle_id, capability)
        if not supported:
            raise CommandUnsupported(
                f'Comando {capability} não está confirmado para o veículo',
            )
        timeout_at = datetime.now() + timedelta(seconds=timeout_seconds)
        cursor.execute(
            "INSERT INTO monitoramento.device_commands "
            "(public_id,vehicle_id,source_code,protocol_code,capability_code,status,"
            "idempotency_key,correlation_id,payload_json,requested_by_type,requested_by_id,"
            "requested_by_name,reason,timeout_at) "
            "VALUES(UUID(),%s,%s,%s,%s,'requested',%s,%s,%s,%s,%s,%s,%s,%s)",
            (vehicle_id, supported['source_code'], supported['protocol_code'], capability,
             idempotency, correlation, json.dumps(command_payload), actor['type'],
             actor['id'], actor['name'], reason, timeout_at),
        )
        command_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO monitoramento.device_command_events "
            "(command_id,from_status,to_status,actor_type,actor_id,event_code,"
            "correlation_id,payload_json) VALUES(%s,NULL,'requested',%s,%s,'requested',%s,%s)",
            (command_id, actor['type'], actor['id'], correlation, json.dumps(command_payload)),
        )
        cursor.execute('SELECT * FROM monitoramento.device_commands WHERE id=%s', (command_id,))
        command = cursor.fetchone()
        conn.commit()
        return _serialize(command, _events(cursor, command_id))
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def transition_command(
    public_id: str, *, target_status: str, expected_version: int,
    actor_type: str, actor_id: str, event_code: str, correlation_id: str,
    message: Optional[str] = None, provider_message_id: Optional[str] = None,
    payload: Optional[Dict] = None,
) -> Dict:
    if actor_type not in {'human', 'system', 'agent', 'provider'}:
        raise CommandError('actor_type inválido')
    if not actor_id or not event_code or not correlation_id:
        raise CommandError('actor_id, event_code e correlation_id são obrigatórios')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            'SELECT * FROM monitoramento.device_commands WHERE public_id=%s FOR UPDATE',
            (public_id,),
        )
        command = cursor.fetchone()
        if not command:
            raise CommandNotFound('Comando não encontrado')
        if int(command['version']) != expected_version:
            raise CommandConflict(
                f'Versão esperada {expected_version}, atual {command["version"]}',
            )
        transition = plan_transition(command['status'], target_status)
        version = expected_version + 1
        cursor.execute(
            "UPDATE monitoramento.device_commands SET status=%s,version=%s,"
            "provider_message_id=COALESCE(%s,provider_message_id),"
            "sent_at=CASE WHEN %s='sent' THEN CURRENT_TIMESTAMP(6) ELSE sent_at END,"
            "finalized_at=CASE WHEN %s THEN CURRENT_TIMESTAMP(6) ELSE finalized_at END,"
            "final_code=CASE WHEN %s THEN %s ELSE final_code END,"
            "final_message=CASE WHEN %s THEN %s ELSE final_message END "
            "WHERE id=%s AND version=%s",
            (target_status, version, provider_message_id, target_status,
             transition['final'], transition['final'], event_code,
             transition['final'], message, command['id'], expected_version),
        )
        if cursor.rowcount != 1:
            raise CommandConflict('Comando alterado concorrentemente')
        cursor.execute(
            "INSERT INTO monitoramento.device_command_events "
            "(command_id,from_status,to_status,actor_type,actor_id,event_code,message,"
            "provider_message_id,correlation_id,payload_json) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (command['id'], command['status'], target_status, actor_type, actor_id,
             event_code, message, provider_message_id, correlation_id,
             json.dumps(payload) if payload is not None else None),
        )
        cursor.execute('SELECT * FROM monitoramento.device_commands WHERE id=%s', (command['id'],))
        updated = cursor.fetchone()
        conn.commit()
        return _serialize(updated, _events(cursor, command['id']))
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def expire_commands(now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    expired = 0
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.device_commands "
            "WHERE status IN ('requested','queued','sent') AND timeout_at<=%s "
            "ORDER BY timeout_at,id FOR UPDATE",
            (now,),
        )
        for command in cursor.fetchall():
            plan_transition(command['status'], 'timed_out')
            version = int(command['version']) + 1
            correlation = f"timeout:{command['public_id']}:{version}"
            cursor.execute(
                "UPDATE monitoramento.device_commands SET status='timed_out',version=%s,"
                "finalized_at=%s,final_code='timeout',final_message='Confirmação não recebida' "
                "WHERE id=%s AND version=%s",
                (version, now, command['id'], command['version']),
            )
            cursor.execute(
                "INSERT IGNORE INTO monitoramento.device_command_events "
                "(command_id,from_status,to_status,actor_type,actor_id,event_code,message,"
                "correlation_id) VALUES(%s,%s,'timed_out','system','command-timeout',"
                "'timeout','Confirmação não recebida',%s)",
                (command['id'], command['status'], correlation),
            )
            expired += 1
        conn.commit()
        return expired
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def run_timeout_worker(interval_seconds: int = 5):
    while True:
        try:
            expire_commands()
        except Exception:
            logger.exception('Falha ao expirar comandos')
        time.sleep(interval_seconds)
