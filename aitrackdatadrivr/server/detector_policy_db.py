"""Versões imutáveis e ativação auditável das políticas de detector."""

import json
from datetime import datetime
from typing import Dict, List, Optional

from .monitor_db import get_connection


VALID_SCOPES = {'global', 'source', 'monitor', 'vehicle'}


def _serialize(row: Dict) -> Dict:
    result = dict(row)
    result['parameters'] = json.loads(result.pop('parameters_json'))
    for key in ('created_at', 'activated_at', 'superseded_at'):
        if isinstance(result.get(key), datetime):
            result[key] = result[key].isoformat()
    return result


def _validate(payload: Dict) -> Dict:
    policy_key = str(payload.get('policy_key') or '').strip().lower()
    detector_type = str(payload.get('detector_type') or '').strip().lower()
    scope_type = str(payload.get('scope_type') or 'global').strip().lower()
    scope_ref = str(payload.get('scope_ref') or '*').strip()
    actor = str(payload.get('created_by') or '').strip()
    reason = str(payload.get('change_reason') or '').strip()
    parameters = payload.get('parameters')
    if not policy_key or not detector_type:
        raise ValueError('policy_key e detector_type são obrigatórios')
    if scope_type not in VALID_SCOPES:
        raise ValueError(f'scope_type inválido: {scope_type}')
    if scope_type == 'global' and scope_ref != '*':
        raise ValueError('escopo global deve usar scope_ref=*')
    if scope_type != 'global' and scope_ref == '*':
        raise ValueError('escopo específico exige scope_ref')
    if not actor or not reason:
        raise ValueError('created_by e change_reason são obrigatórios')
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError('parameters deve ser um objeto JSON não vazio')
    return {
        'policy_key': policy_key,
        'detector_type': detector_type,
        'capability_code': payload.get('capability_code'),
        'scope_type': scope_type,
        'scope_ref': scope_ref,
        'parameters_json': json.dumps(parameters, separators=(',', ':'), sort_keys=True),
        'created_by': actor,
        'change_reason': reason,
    }


def list_policies(status: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        where = ' WHERE status = %s' if status else ''
        cursor.execute(
            "SELECT id, policy_key, version_number, detector_type, capability_code, "
            "scope_type, scope_ref, parameters_json, status, created_by, "
            "change_reason, created_at, activated_at, superseded_at "
            f"FROM monitoramento.detector_policies{where} "
            "ORDER BY policy_key, scope_type, scope_ref, version_number DESC",
            (status,) if status else (),
        )
        return [_serialize(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def create_policy(payload: Dict) -> Dict:
    data = _validate(payload)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT version_number FROM monitoramento.detector_policies "
            "WHERE policy_key = %s AND scope_type = %s AND scope_ref = %s FOR UPDATE",
            (data['policy_key'], data['scope_type'], data['scope_ref']),
        )
        versions = [int(row['version_number']) for row in cursor.fetchall()]
        version = max(versions, default=0) + 1
        cursor.execute(
            "INSERT INTO monitoramento.detector_policies "
            "(policy_key, version_number, detector_type, capability_code, "
            "scope_type, scope_ref, parameters_json, created_by, change_reason) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                data['policy_key'], version, data['detector_type'],
                data['capability_code'], data['scope_type'], data['scope_ref'],
                data['parameters_json'], data['created_by'], data['change_reason'],
            ),
        )
        policy_id = cursor.lastrowid
        cursor.execute(
            "SELECT * FROM monitoramento.detector_policies WHERE id = %s",
            (policy_id,),
        )
        row = cursor.fetchone()
        cursor.execute(
            "INSERT INTO monitoramento.detector_policy_audit "
            "(policy_id, event_type, actor, reason, snapshot_json, correlation_id) "
            "VALUES (%s, 'created', %s, %s, %s, %s)",
            (
                policy_id, data['created_by'], data['change_reason'],
                json.dumps(_serialize(row), separators=(',', ':'), sort_keys=True),
                payload.get('correlation_id'),
            ),
        )
        conn.commit()
        return _serialize(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def activate_policy(policy_id: int, actor: str, reason: str, correlation_id=None) -> Dict:
    actor, reason = str(actor or '').strip(), str(reason or '').strip()
    if not actor or not reason:
        raise ValueError('actor e reason são obrigatórios')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.detector_policies WHERE id = %s FOR UPDATE",
            (policy_id,),
        )
        target = cursor.fetchone()
        if not target:
            raise LookupError('Política não encontrada')
        if target['status'] not in ('draft', 'active'):
            raise ValueError('Somente política draft ou active pode ser ativada')
        active_key = f"{target['policy_key']}:{target['scope_type']}:{target['scope_ref']}"
        cursor.execute(
            "SELECT * FROM monitoramento.detector_policies "
            "WHERE active_key = %s AND id <> %s FOR UPDATE",
            (active_key, policy_id),
        )
        previous = cursor.fetchone()
        if previous:
            cursor.execute(
                "UPDATE monitoramento.detector_policies SET status='superseded', "
                "active_key=NULL, superseded_at=CURRENT_TIMESTAMP(6) WHERE id=%s",
                (previous['id'],),
            )
            cursor.execute(
                "INSERT INTO monitoramento.detector_policy_audit "
                "(policy_id,event_type,actor,reason,snapshot_json,correlation_id) "
                "VALUES (%s,'superseded',%s,%s,%s,%s)",
                (
                    previous['id'], actor, reason,
                    json.dumps(_serialize(previous), separators=(',', ':'), sort_keys=True),
                    correlation_id,
                ),
            )
        cursor.execute(
            "UPDATE monitoramento.detector_policies SET status='active', active_key=%s, "
            "activated_at=COALESCE(activated_at,CURRENT_TIMESTAMP(6)) WHERE id=%s",
            (active_key, policy_id),
        )
        cursor.execute(
            "SELECT * FROM monitoramento.detector_policies WHERE id = %s",
            (policy_id,),
        )
        activated = cursor.fetchone()
        cursor.execute(
            "INSERT INTO monitoramento.detector_policy_audit "
            "(policy_id,event_type,actor,reason,snapshot_json,correlation_id) "
            "VALUES (%s,'activated',%s,%s,%s,%s)",
            (
                policy_id, actor, reason,
                json.dumps(_serialize(activated), separators=(',', ':'), sort_keys=True),
                correlation_id,
            ),
        )
        conn.commit()
        return _serialize(activated)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
