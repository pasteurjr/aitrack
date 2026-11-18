"""Detector conservador de perda de alimentação e baixa tensão externa."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .monitor_db import get_connection


@dataclass(frozen=True)
class DetectorPlan:
    state: str
    trigger_count: int
    recovery_count: int
    action: Optional[str] = None


def validate_parameters(parameters: Dict) -> Dict:
    required = ('trigger_below_v', 'recover_above_v', 'trigger_samples', 'recover_samples')
    if any(name not in parameters for name in required):
        raise ValueError('Política de tensão incompleta')
    trigger = float(parameters['trigger_below_v'])
    recover = float(parameters['recover_above_v'])
    trigger_samples = int(parameters['trigger_samples'])
    recover_samples = int(parameters['recover_samples'])
    if trigger < 0 or recover <= trigger:
        raise ValueError('Histerese inválida: recuperação deve superar disparo')
    if trigger_samples < 2 or recover_samples < 2:
        raise ValueError('Detector exige ao menos duas amostras consecutivas')
    return {
        **parameters,
        'trigger_below_v': trigger,
        'recover_above_v': recover,
        'trigger_samples': trigger_samples,
        'recover_samples': recover_samples,
        'trigger_above_v': (
            float(parameters['trigger_above_v'])
            if parameters.get('trigger_above_v') is not None else None
        ),
        'cooldown_seconds': max(int(parameters.get('cooldown_seconds', 0)), 0),
    }


def plan_reading(state: str, trigger_count: int, recovery_count: int, value: float, parameters: Dict) -> DetectorPlan:
    """Máquina pura: facilita provar falso positivo/negativo e histerese."""
    params = validate_parameters(parameters)
    is_low = value <= params['trigger_below_v']
    if params['trigger_above_v'] is not None:
        is_low = is_low and value > params['trigger_above_v']
    is_recovered = value >= params['recover_above_v']

    if state in {'active', 'recovery_pending'}:
        if is_recovered:
            recovery_count += 1
            if recovery_count >= params['recover_samples']:
                return DetectorPlan('normal', 0, 0, 'resolve')
            return DetectorPlan('recovery_pending', 0, recovery_count)
        return DetectorPlan('active', 0, 0)

    if is_low:
        trigger_count += 1
        if trigger_count >= params['trigger_samples']:
            return DetectorPlan('active', 0, 0, 'open')
        return DetectorPlan('trigger_pending', trigger_count, 0)
    return DetectorPlan('normal', 0, 0)


def _active_policies(cursor, vehicle_id: int):
    cursor.execute(
        "SELECT p.* FROM monitoramento.detector_policies p "
        "WHERE p.status='active' AND p.capability_code='external_voltage' "
        "AND p.detector_type IN ('power_removed','low_external_voltage') "
        "AND (p.scope_type='global' "
        "OR (p.scope_type='source' AND p.scope_ref='tracker') "
        "OR (p.scope_type='vehicle' AND p.scope_ref=%s)) "
        "ORDER BY CASE p.detector_type WHEN 'power_removed' THEN 1 ELSE 2 END",
        (str(vehicle_id),),
    )
    return cursor.fetchall()


def evaluate_external_voltage(
    cursor, *, sensor_id: int, vehicle_id: Optional[int], reading_id: int,
    value: float, received_at: datetime,
) -> list:
    """Avalia leitura já persistida; sem veículo armado não cria episódio."""
    if vehicle_id is None:
        return []
    cursor.execute(
        "SELECT state FROM monitoramento.vehicle_security_state "
        "WHERE vehicle_id=%s FOR UPDATE",
        (vehicle_id,),
    )
    security = cursor.fetchone()
    if not security or security['state'] != 'armed':
        return []

    results = []
    for policy in _active_policies(cursor, vehicle_id):
        parameters = validate_parameters(json.loads(policy['parameters_json']))
        cursor.execute(
            "INSERT IGNORE INTO monitoramento.detector_signal_state "
            "(policy_id,sensor_id,last_reading_id,last_value) VALUES (%s,%s,%s,%s)",
            (policy['id'], sensor_id, reading_id, value),
        )
        cursor.execute(
            "SELECT * FROM monitoramento.detector_signal_state "
            "WHERE policy_id=%s AND sensor_id=%s FOR UPDATE",
            (policy['id'], sensor_id),
        )
        current = cursor.fetchone()
        if current['cooldown_until'] and received_at < current['cooldown_until']:
            cursor.execute(
                "UPDATE monitoramento.detector_signal_state SET last_reading_id=%s,"
                "last_value=%s WHERE policy_id=%s AND sensor_id=%s",
                (reading_id, value, policy['id'], sensor_id),
            )
            results.append({'policy_id': policy['id'], 'action': 'cooldown'})
            continue

        plan = plan_reading(
            current['state'], int(current['trigger_count']),
            int(current['recovery_count']), float(value), parameters,
        )
        episode_id = current['active_episode_id']
        if plan.action == 'open':
            correlation = f"voltage:{policy['id']}:{sensor_id}:{reading_id}"
            cursor.execute(
                "INSERT INTO monitoramento.detector_episodes "
                "(public_id,policy_id,sensor_id,vehicle_id,episode_type,status,severity,"
                "correlation_key,started_at,trigger_value,minimum_value,metadata_json) "
                "VALUES (UUID(),%s,%s,%s,%s,'open',%s,%s,%s,%s,%s,%s)",
                (policy['id'], sensor_id, vehicle_id, policy['detector_type'],
                 parameters.get('severity', 'high'), correlation, received_at,
                 value, value, json.dumps({'reading_id': reading_id})),
            )
            episode_id = cursor.lastrowid
        elif episode_id and current['state'] in {'active', 'recovery_pending'}:
            cursor.execute(
                "UPDATE monitoramento.detector_episodes SET minimum_value=LEAST(minimum_value,%s),"
                "evidence_count=evidence_count+1 WHERE id=%s AND status='open'",
                (value, episode_id),
            )
        if plan.action == 'resolve' and episode_id:
            cursor.execute(
                "UPDATE monitoramento.detector_episodes SET status='resolved',resolved_at=%s,"
                "recovery_value=%s WHERE id=%s AND status='open'",
                (received_at, value, episode_id),
            )
            episode_id = None

        cooldown_until = None
        if plan.action == 'resolve' and parameters['cooldown_seconds']:
            cooldown_until = received_at + timedelta(seconds=parameters['cooldown_seconds'])
        cursor.execute(
            "UPDATE monitoramento.detector_signal_state SET state=%s,trigger_count=%s,"
            "recovery_count=%s,active_episode_id=%s,last_reading_id=%s,last_value=%s,"
            "cooldown_until=%s WHERE policy_id=%s AND sensor_id=%s",
            (plan.state, plan.trigger_count, plan.recovery_count, episode_id,
             reading_id, value, cooldown_until, policy['id'], sensor_id),
        )
        results.append({
            'policy_id': policy['id'], 'state': plan.state,
            'action': plan.action, 'episode_id': episode_id,
        })
    return results


def list_episodes(vehicle_id: int, status: Optional[str] = None, limit: int = 50) -> Dict:
    if status not in {None, 'open', 'resolved'}:
        raise ValueError('status deve ser open ou resolved')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conditions = ['e.vehicle_id=%s']
        params = [vehicle_id]
        if status:
            conditions.append('e.status=%s')
            params.append(status)
        params.append(min(max(int(limit), 1), 200))
        cursor.execute(
            "SELECT e.id,e.public_id,e.vehicle_id,e.episode_type,e.status,e.severity,"
            "e.started_at,e.resolved_at,e.trigger_value,e.recovery_value,"
            "e.minimum_value,e.evidence_count,p.policy_key,p.version_number,"
            "s.source_code,s.protocol_code,s.capability_code "
            "FROM monitoramento.detector_episodes e "
            "JOIN monitoramento.detector_policies p ON p.id=e.policy_id "
            "JOIN monitoramento.sensors s ON s.id=e.sensor_id "
            f"WHERE {' AND '.join(conditions)} "
            "ORDER BY e.started_at DESC,e.id DESC LIMIT %s",
            params,
        )
        episodes = cursor.fetchall()
        for episode in episodes:
            for field in ('started_at', 'resolved_at'):
                if isinstance(episode.get(field), datetime):
                    episode[field] = episode[field].isoformat()
            for field in ('trigger_value', 'recovery_value', 'minimum_value'):
                if episode.get(field) is not None:
                    episode[field] = float(episode[field])
        return {
            'schema_version': 'detector-episodes.v1',
            'vehicle_id': vehicle_id,
            'count': len(episodes),
            'episodes': episodes,
        }
    finally:
        cursor.close()
        conn.close()
