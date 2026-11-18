"""Máquina de estado patrimonial com concorrência e histórico auditável."""

from datetime import datetime
from typing import Dict

from .monitor_db import get_connection


VALID_STATES = {'disarmed', 'armed'}
VALID_ACTOR_TYPES = {'human', 'system'}
VALID_AUTHORIZATION = {'owner_request', 'operator_protocol', 'scheduled_policy'}


class SecurityStateError(ValueError):
    code = 'INVALID_SECURITY_TRANSITION'


class SecurityStateNotFound(SecurityStateError):
    code = 'VEHICLE_NOT_FOUND'


class SecurityStateConflict(SecurityStateError):
    code = 'SECURITY_STATE_VERSION_CONFLICT'


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize_state(row: Dict, history=None, idempotent=False) -> Dict:
    return {
        'schema_version': 'vehicle-security-state.v1',
        'vehicle_id': int(row['vehicle_id']),
        'state': row['state'],
        'version': int(row['version']),
        'changed_by': {
            'type': row['changed_by_type'],
            'id': row['changed_by_id'],
            'name': row['changed_by_name'],
        },
        'authorization_basis': row['authorization_basis'],
        'reason': row['reason'],
        'changed_at': _iso(row['changed_at']),
        'history': history or [],
        'idempotent': idempotent,
    }


def _history(cursor, vehicle_id: int, limit=20):
    cursor.execute(
        "SELECT id,from_state,to_state,from_version,to_version,actor_type,actor_id,"
        "actor_name,authorization_basis,reason,correlation_id,occurred_at "
        "FROM monitoramento.vehicle_security_history WHERE vehicle_id=%s "
        "ORDER BY occurred_at DESC,id DESC LIMIT %s",
        (vehicle_id, min(max(int(limit), 1), 100)),
    )
    rows = cursor.fetchall()
    for row in rows:
        row['occurred_at'] = _iso(row['occurred_at'])
    return rows


def get_state(vehicle_id: int, history_limit=20):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT s.* FROM monitoramento.vehicle_security_state s "
            "JOIN monitoramento.veiculos v ON v.id=s.vehicle_id "
            "WHERE s.vehicle_id=%s AND v.merged_into_id IS NULL",
            (vehicle_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _serialize_state(row, _history(cursor, vehicle_id, history_limit))
    finally:
        cursor.close()
        conn.close()


def transition(vehicle_id: int, payload: Dict) -> Dict:
    target = str(payload.get('target_state') or '').strip().lower()
    actor = payload.get('actor') if isinstance(payload.get('actor'), dict) else {}
    actor_type = str(actor.get('type') or '').strip().lower()
    actor_id = str(actor.get('id') or '').strip()
    actor_name = str(actor.get('name') or '').strip()
    basis = str(payload.get('authorization_basis') or '').strip().lower()
    reason = str(payload.get('reason') or '').strip()
    correlation = str(payload.get('correlation_id') or '').strip()
    expected_version = payload.get('expected_version')
    if target not in VALID_STATES:
        raise SecurityStateError('target_state inválido')
    if actor_type not in VALID_ACTOR_TYPES or not actor_id or not actor_name:
        raise SecurityStateError('actor completo e tipo human/system são obrigatórios')
    if basis not in VALID_AUTHORIZATION:
        raise SecurityStateError('authorization_basis inválida')
    if basis == 'scheduled_policy' and actor_type != 'system':
        raise SecurityStateError('scheduled_policy exige actor system')
    if basis in {'owner_request', 'operator_protocol'} and actor_type != 'human':
        raise SecurityStateError(f'{basis} exige actor human')
    if len(reason) < 5 or not correlation:
        raise SecurityStateError('reason (mín. 5) e correlation_id são obrigatórios')
    if not isinstance(expected_version, int) or expected_version < 1:
        raise SecurityStateError('expected_version positivo é obrigatório')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.vehicle_security_history "
            "WHERE vehicle_id=%s AND correlation_id=%s FOR UPDATE",
            (vehicle_id, correlation),
        )
        repeated = cursor.fetchone()
        if repeated:
            if repeated['to_state'] != target:
                raise SecurityStateConflict('correlation_id já usado para outro destino')
            cursor.execute(
                'SELECT * FROM monitoramento.vehicle_security_state WHERE vehicle_id=%s',
                (vehicle_id,),
            )
            row = cursor.fetchone()
            conn.commit()
            return _serialize_state(row, _history(cursor, vehicle_id), idempotent=True)

        cursor.execute(
            "SELECT s.* FROM monitoramento.vehicle_security_state s "
            "JOIN monitoramento.veiculos v ON v.id=s.vehicle_id "
            "WHERE s.vehicle_id=%s AND v.merged_into_id IS NULL FOR UPDATE",
            (vehicle_id,),
        )
        current = cursor.fetchone()
        if not current:
            raise SecurityStateNotFound('Veículo ou estado patrimonial não encontrado')
        if int(current['version']) != expected_version:
            raise SecurityStateConflict(
                f'Versão esperada {expected_version}, atual {current["version"]}',
            )
        if current['state'] == target:
            raise SecurityStateError(f'Veículo já está {target}')
        next_version = expected_version + 1
        cursor.execute(
            "UPDATE monitoramento.vehicle_security_state SET state=%s,version=%s,"
            "changed_by_type=%s,changed_by_id=%s,changed_by_name=%s,"
            "authorization_basis=%s,reason=%s,changed_at=CURRENT_TIMESTAMP(6) "
            "WHERE vehicle_id=%s AND version=%s",
            (target, next_version, actor_type, actor_id, actor_name, basis, reason,
             vehicle_id, expected_version),
        )
        if cursor.rowcount != 1:
            raise SecurityStateConflict('Estado foi alterado por outro operador')
        cursor.execute(
            "INSERT INTO monitoramento.vehicle_security_history "
            "(vehicle_id,from_state,to_state,from_version,to_version,actor_type,"
            "actor_id,actor_name,authorization_basis,reason,correlation_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (vehicle_id, current['state'], target, expected_version, next_version,
             actor_type, actor_id, actor_name, basis, reason, correlation),
        )
        cursor.execute(
            'SELECT * FROM monitoramento.vehicle_security_state WHERE vehicle_id=%s',
            (vehicle_id,),
        )
        updated = cursor.fetchone()
        conn.commit()
        return _serialize_state(updated, _history(cursor, vehicle_id))
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
