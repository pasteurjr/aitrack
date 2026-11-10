"""Snapshot operacional de cercas, alvos e último estado avaliado."""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .geofence_db import GEOFENCE_SELECT, _serialize as serialize_geofence
from .geofence_engine import SYSTEM_TIMEZONE, schedule_is_active
from .monitor_db import get_connection


ASSIGNMENT_STATE_SELECT = """
    SELECT ga.id AS assignment_id, ga.geofence_id, ga.target_type,
           ga.vehicle_id AS assigned_vehicle_id,
           ga.driver_id AS assigned_driver_id, ga.group_id,
           ga.timezone_name, ga.effective_from, ga.effective_to,
           ga.dwell_threshold_seconds, ga.hysteresis_meters,
           CASE ga.target_type
             WHEN 'vehicle' THEN COALESCE(v.placa, v.descricao, CONCAT('Veículo #', v.id))
             WHEN 'driver' THEN COALESCE(d.nome, CONCAT('Motorista #', d.id))
             WHEN 'group' THEN mg.nome
           END AS target_label,
           s.subject_type, s.vehicle_id AS state_vehicle_id,
           s.driver_id AS state_driver_id, s.stable_state, s.pending_state,
           s.pending_samples, s.last_signed_distance_m, s.last_latitude,
           s.last_longitude, s.last_accuracy_m, s.last_source,
           s.last_observed_at, s.last_transition_at, s.violation_started_at,
           s.dwell_notified_at, s.violation_episode_id,
           CASE s.subject_type
             WHEN 'vehicle' THEN COALESCE(sv.placa, sv.descricao, CONCAT('Veículo #', sv.id))
             WHEN 'driver' THEN COALESCE(sd.nome, CONCAT('Motorista #', sd.id))
           END AS subject_label
      FROM monitoramento.geofence_assignments ga
 LEFT JOIN monitoramento.veiculos v ON v.id = ga.vehicle_id
 LEFT JOIN monitoramento.motoristas d ON d.id = ga.driver_id
 LEFT JOIN monitoramento.monitoring_groups mg ON mg.id = ga.group_id
 LEFT JOIN monitoramento.geofence_target_states s ON s.assignment_id = ga.id
 LEFT JOIN monitoramento.veiculos sv ON sv.id = s.vehicle_id
 LEFT JOIN monitoramento.motoristas sd ON sd.id = s.driver_id
     WHERE ga.ativo = TRUE AND ga.geofence_id IN ({placeholders})
     ORDER BY ga.priority, ga.id, s.subject_type, s.id
"""


def _value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _effective_now(row: Dict, now: datetime) -> bool:
    try:
        zone = ZoneInfo(row['timezone_name'])
    except ZoneInfoNotFoundError:
        return False
    system_zone = ZoneInfo(SYSTEM_TIMEZONE)
    aware = now.replace(tzinfo=system_zone) if now.tzinfo is None else now
    local_date = aware.astimezone(zone).date()
    return not (
        row['effective_from'] is not None and local_date < row['effective_from']
    ) and not (
        row['effective_to'] is not None and local_date > row['effective_to']
    )


def build_live_state(
    geofences: List[Dict], assignment_rows: List[Dict],
    schedules_by_assignment: Dict[int, List[Dict]], now: datetime,
) -> List[Dict]:
    """Monta o contrato sem fazer I/O, facilitando prova de regras temporais."""
    result = []
    by_fence: Dict[int, List[Dict]] = {}
    rule_by_fence = {fence['id']: fence['regra'] for fence in geofences}
    active_fence_ids = {
        fence['id'] for fence in geofences if fence['status'] == 'active'
    }
    for row in assignment_rows:
        schedules = schedules_by_assignment.get(row['assignment_id'], [])
        effective = _effective_now(row, now)
        schedule_active = effective and schedule_is_active(
            now, row['timezone_name'], schedules,
        )
        policy_active = (
            row['geofence_id'] in active_fence_ids and schedule_active
        )
        stable_state = row.get('stable_state') or 'unknown'
        rule = rule_by_fence[row['geofence_id']]
        violation_state = 'outside' if rule == 'allowed' else 'inside'
        subject_type = row.get('subject_type')
        subject_id = (
            row.get('state_vehicle_id') if subject_type == 'vehicle'
            else row.get('state_driver_id') if subject_type == 'driver' else None
        )
        target = {
            'assignment_id': row['assignment_id'],
            'target_type': row['target_type'],
            'target_label': row.get('target_label'),
            'subject_type': subject_type,
            'subject_id': subject_id,
            'subject_label': row.get('subject_label') or row.get('target_label'),
            'stable_state': stable_state,
            'pending_state': row.get('pending_state'),
            'pending_samples': int(row.get('pending_samples') or 0),
            'policy_active': policy_active,
            'schedule_active': schedule_active,
            'timezone_name': row['timezone_name'],
            'effective_from': _value(row.get('effective_from')),
            'effective_to': _value(row.get('effective_to')),
            'schedules': [{key: _value(value) for key, value in item.items()}
                          for item in schedules],
            'dwell_threshold_seconds': row.get('dwell_threshold_seconds'),
            'hysteresis_meters': _value(row.get('hysteresis_meters')),
            'is_violation': policy_active and stable_state == violation_state,
            'active_episode': bool(
                policy_active and row.get('violation_episode_id')
            ),
            'violation_episode_id': row.get('violation_episode_id'),
            'violation_started_at': _value(row.get('violation_started_at')),
            'dwell_notified_at': _value(row.get('dwell_notified_at')),
            'last_evaluated_at': _value(row.get('last_observed_at')),
            'last_transition_at': _value(row.get('last_transition_at')),
            'last_source': row.get('last_source'),
            'last_position': None if row.get('last_latitude') is None else {
                'latitude': float(row['last_latitude']),
                'longitude': float(row['last_longitude']),
                'accuracy_m': _value(row.get('last_accuracy_m')),
                'signed_distance_m': _value(row.get('last_signed_distance_m')),
            },
        }
        by_fence.setdefault(row['geofence_id'], []).append(target)

    for fence_row in geofences:
        fence = serialize_geofence(fence_row)
        targets = by_fence.get(fence['id'], [])
        fence['targets'] = targets
        fence['live_summary'] = {
            'targets': len(targets),
            'inside': sum(item['stable_state'] == 'inside' for item in targets),
            'outside': sum(item['stable_state'] == 'outside' for item in targets),
            'unknown': sum(item['stable_state'] == 'unknown' for item in targets),
            'violations': sum(bool(item['is_violation']) for item in targets),
            'active_episodes': sum(bool(item['active_episode']) for item in targets),
        }
        result.append(fence)
    return result


def get_live_state(limit: int = 200, now: datetime | None = None) -> List[Dict]:
    now = now or datetime.now()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            GEOFENCE_SELECT
            + " WHERE g.status <> 'archived' ORDER BY g.status = 'active' DESC, g.nome, g.id"
            + ' LIMIT %s',
            (limit,),
        )
        geofences = cursor.fetchall()
        if not geofences:
            return []
        fence_ids = [row['id'] for row in geofences]
        placeholders = ','.join(['%s'] * len(fence_ids))
        cursor.execute(
            ASSIGNMENT_STATE_SELECT.format(placeholders=placeholders),
            tuple(fence_ids),
        )
        assignment_rows = cursor.fetchall()
        assignment_ids = sorted({row['assignment_id'] for row in assignment_rows})
        schedules_by_assignment: Dict[int, List[Dict]] = {}
        if assignment_ids:
            assignment_placeholders = ','.join(['%s'] * len(assignment_ids))
            cursor.execute(f"""
                SELECT assignment_id, day_of_week,
                       CAST(start_time AS CHAR) AS start_time,
                       CAST(end_time AS CHAR) AS end_time, crosses_midnight
                  FROM monitoramento.geofence_assignment_schedules
                 WHERE ativo = TRUE
                   AND assignment_id IN ({assignment_placeholders})
                 ORDER BY assignment_id, day_of_week, start_time, id
            """, tuple(assignment_ids))
            for schedule in cursor.fetchall():
                schedules_by_assignment.setdefault(schedule['assignment_id'], []).append({
                    'day_of_week': schedule['day_of_week'],
                    'start_time': schedule['start_time'],
                    'end_time': schedule['end_time'],
                    'crosses_midnight': bool(schedule['crosses_midnight']),
                })
        return build_live_state(geofences, assignment_rows, schedules_by_assignment, now)
    finally:
        cursor.close()
        conn.close()
