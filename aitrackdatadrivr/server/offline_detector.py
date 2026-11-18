"""Detecção periódica de offline com supressões operacionais explícitas."""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from .monitor_db import get_connection


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OfflinePlan:
    state: str
    stale_checks: int
    recovery_checks: int
    action: Optional[str] = None


def validate_parameters(parameters: Dict) -> Dict:
    required = (
        'expected_interval_seconds', 'moving_grace_seconds',
        'ignition_grace_seconds', 'idle_grace_seconds',
        'integration_outage_seconds', 'trigger_checks', 'recovery_checks',
    )
    if any(name not in parameters for name in required):
        raise ValueError('Política offline incompleta')
    parsed = {**parameters}
    for name in required:
        parsed[name] = int(parameters[name])
    if parsed['expected_interval_seconds'] < 1:
        raise ValueError('expected_interval_seconds inválido')
    if not (
        parsed['moving_grace_seconds'] >= parsed['expected_interval_seconds']
        and parsed['ignition_grace_seconds'] >= parsed['moving_grace_seconds']
        and parsed['idle_grace_seconds'] >= parsed['ignition_grace_seconds']
    ):
        raise ValueError('Janelas offline devem crescer de movimento para repouso')
    if parsed['trigger_checks'] < 2 or parsed['recovery_checks'] < 2:
        raise ValueError('Offline exige ao menos duas verificações consecutivas')
    return parsed


def context_threshold(parameters: Dict, *, ignition: Optional[bool], speed: Optional[float]):
    params = validate_parameters(parameters)
    if speed is not None and speed > 5:
        return 'moving', params['moving_grace_seconds']
    if ignition is True:
        return 'ignition_on', params['ignition_grace_seconds']
    return 'idle_or_unknown', params['idle_grace_seconds']


def plan_check(state: str, stale_checks: int, recovery_checks: int, *, stale: bool, parameters: Dict) -> OfflinePlan:
    params = validate_parameters(parameters)
    if state in {'offline', 'recovery_pending'}:
        if stale:
            return OfflinePlan('offline', 0, 0)
        recovery_checks += 1
        if recovery_checks >= params['recovery_checks']:
            return OfflinePlan('normal', 0, 0, 'resolve')
        return OfflinePlan('recovery_pending', 0, recovery_checks)
    if stale:
        stale_checks += 1
        if stale_checks >= params['trigger_checks']:
            return OfflinePlan('offline', 0, 0, 'open')
        return OfflinePlan('suspect', stale_checks, 0)
    return OfflinePlan('normal', 0, 0)


def suppression_reason(
    *, security_state: Optional[str], integration_status: Optional[str],
    integration_last_success: Optional[datetime], maintenance_until: Optional[datetime],
    now: datetime, parameters: Dict,
) -> Optional[str]:
    params = validate_parameters(parameters)
    if security_state != 'armed':
        return 'vehicle_disarmed'
    integration_stale = (
        integration_last_success is None
        or (now - integration_last_success).total_seconds()
            > params['integration_outage_seconds']
    )
    if integration_status == 'outage' or integration_stale:
        return 'integration_outage'
    if maintenance_until and maintenance_until > now:
        return 'maintenance'
    return None


def record_source_success(cursor, source_code: str, occurred_at: datetime):
    cursor.execute(
        "INSERT INTO monitoramento.integration_health "
        "(source_code,status,last_success_at,reason) VALUES (%s,'healthy',%s,NULL) "
        "ON DUPLICATE KEY UPDATE status='healthy',last_success_at=VALUES(last_success_at),"
        "reason=NULL",
        (source_code, occurred_at),
    )


def _latest_value(cursor, vehicle_id: int, capability_code: str):
    cursor.execute(
        "SELECT r.value_json,r.created_at FROM monitoramento.sensors s "
        "JOIN monitoramento.sensor_readings r ON r.sensor_id=s.id "
        "WHERE s.vehicle_id=%s AND s.source_code='tracker' "
        "AND s.capability_code=%s ORDER BY r.created_at DESC,r.id DESC LIMIT 1",
        (vehicle_id, capability_code),
    )
    row = cursor.fetchone()
    if not row:
        return None, None
    return json.loads(row['value_json']), row['created_at']


def evaluate_vehicle(cursor, *, policy: Dict, vehicle_id: int, now: datetime) -> Dict:
    params = validate_parameters(json.loads(policy['parameters_json']))
    cursor.execute(
        "INSERT IGNORE INTO monitoramento.offline_detector_state "
        "(policy_id,vehicle_id) VALUES (%s,%s)", (policy['id'], vehicle_id),
    )
    cursor.execute(
        "SELECT * FROM monitoramento.offline_detector_state "
        "WHERE policy_id=%s AND vehicle_id=%s FOR UPDATE",
        (policy['id'], vehicle_id),
    )
    current = cursor.fetchone()
    cursor.execute(
        "SELECT state FROM monitoramento.vehicle_security_state WHERE vehicle_id=%s",
        (vehicle_id,),
    )
    security = cursor.fetchone()
    cursor.execute(
        "SELECT status,last_success_at FROM monitoramento.integration_health "
        "WHERE source_code='tracker'",
    )
    integration = cursor.fetchone()
    cursor.execute(
        "SELECT maintenance_until FROM monitoramento.vehicle_monitoring_context "
        "WHERE vehicle_id=%s", (vehicle_id,),
    )
    maintenance = cursor.fetchone()
    suppression = suppression_reason(
        security_state=security['state'] if security else None,
        integration_status=integration['status'] if integration else None,
        integration_last_success=integration['last_success_at'] if integration else None,
        maintenance_until=maintenance['maintenance_until'] if maintenance else None,
        now=now, parameters=params,
    )

    if suppression:
        cursor.execute(
            "UPDATE monitoramento.offline_detector_state SET suppressed_reason=%s,"
            "last_evaluated_at=%s WHERE policy_id=%s AND vehicle_id=%s",
            (suppression, now, policy['id'], vehicle_id),
        )
        return {'suppressed': suppression, 'action': None}

    _position, position_at = _latest_value(cursor, vehicle_id, 'position')
    ignition, _ignition_at = _latest_value(cursor, vehicle_id, 'ignition')
    speed, _speed_at = _latest_value(cursor, vehicle_id, 'speed')
    context, threshold = context_threshold(params, ignition=ignition, speed=speed)
    age = None if position_at is None else max((now - position_at).total_seconds(), 0)
    stale = position_at is None or age > threshold
    plan = plan_check(
        current['state'], int(current['stale_checks']),
        int(current['recovery_checks']), stale=stale, parameters=params,
    )
    episode_id = current['active_episode_id']
    if plan.action == 'open':
        correlation = f"offline:{policy['id']}:{vehicle_id}:{int(now.timestamp())}"
        cursor.execute(
            "SELECT id FROM monitoramento.sensors WHERE vehicle_id=%s "
            "AND source_code='tracker' AND capability_code='position' LIMIT 1",
            (vehicle_id,),
        )
        sensor = cursor.fetchone()
        if not sensor:
            return {'suppressed': 'position_sensor_absent', 'action': None}
        cursor.execute(
            "INSERT INTO monitoramento.detector_episodes "
            "(public_id,policy_id,sensor_id,vehicle_id,episode_type,status,severity,"
            "correlation_key,started_at,trigger_value,minimum_value,metadata_json) "
            "VALUES(UUID(),%s,%s,%s,'offline','open',%s,%s,%s,%s,%s,%s)",
            (policy['id'], sensor['id'], vehicle_id, params.get('severity', 'high'),
             correlation, now, age or 0, age or 0,
             json.dumps({'context': context, 'threshold_seconds': threshold})),
        )
        episode_id = cursor.lastrowid
    elif plan.action == 'resolve' and episode_id:
        cursor.execute(
            "UPDATE monitoramento.detector_episodes SET status='resolved',resolved_at=%s,"
            "recovery_value=%s WHERE id=%s AND status='open'",
            (now, age or 0, episode_id),
        )
        episode_id = None
    cursor.execute(
        "UPDATE monitoramento.offline_detector_state SET state=%s,stale_checks=%s,"
        "recovery_checks=%s,active_episode_id=%s,last_position_at=%s,last_context=%s,"
        "suppressed_reason=NULL,last_evaluated_at=%s WHERE policy_id=%s AND vehicle_id=%s",
        (plan.state, plan.stale_checks, plan.recovery_checks, episode_id, position_at,
         context, now, policy['id'], vehicle_id),
    )
    return {'action': plan.action, 'state': plan.state, 'context': context, 'age': age}


def evaluate_due(now: Optional[datetime] = None) -> list:
    now = now or datetime.now()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    results = []
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.detector_policies WHERE status='active' "
            "AND detector_type='offline' AND capability_code='position'",
        )
        policies = cursor.fetchall()
        for policy in policies:
            cursor.execute(
                "SELECT DISTINCT s.vehicle_id FROM monitoramento.sensors s "
                "WHERE s.source_code='tracker' AND s.capability_code='position' "
                "AND s.vehicle_id IS NOT NULL",
            )
            for row in cursor.fetchall():
                result = evaluate_vehicle(
                    cursor, policy=policy, vehicle_id=int(row['vehicle_id']), now=now,
                )
                results.append({'vehicle_id': int(row['vehicle_id']), **result})
        conn.commit()
        return results
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def run_forever(interval_seconds: int = 30):
    while True:
        try:
            evaluate_due()
        except Exception:
            logger.exception('Falha no ciclo do detector offline')
        time.sleep(interval_seconds)
