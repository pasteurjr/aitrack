"""Avalia posições das duas fontes contra cercas operacionais.

O motor mantém um estado por vínculo e alvo canônico. A banda de histerese
absorve oscilações de GPS junto à borda e uma mudança só é confirmada após
amostras consecutivas. A primeira posição confiável estabelece a linha de
base e nunca gera um falso evento de entrada/saída.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import datetime, time as datetime_time, timedelta
from typing import Dict, List, NamedTuple, Optional, Tuple
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .incident_correlator import correlate_geofence_event
from .monitor_db import get_connection


LOGGER = logging.getLogger(__name__)
EARTH_RADIUS_M = 6_371_008.8
CONFIRMATION_SAMPLES = max(1, int(os.getenv('GEOFENCE_CONFIRMATION_SAMPLES', '2')))
CACHE_TTL_SECONDS = max(1, int(os.getenv('GEOFENCE_CACHE_TTL_SECONDS', '60')))
SYSTEM_TIMEZONE = os.getenv('AITRACK_TIMEZONE', 'America/Sao_Paulo')
Point = Tuple[float, float]
_assignment_cache: Dict[Tuple, Tuple[float, List[Dict]]] = {}
_cache_lock = threading.Lock()


class StateEvolution(NamedTuple):
    stable_state: str
    pending_state: Optional[str]
    pending_samples: int
    transition: Optional[Tuple[str, str]]


def _haversine_m(first: Point, second: Point) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))


def _project(point: Point, reference_latitude: float) -> Point:
    longitude, latitude = map(math.radians, point)
    return (
        EARTH_RADIUS_M * longitude * math.cos(math.radians(reference_latitude)),
        EARTH_RADIUS_M * latitude,
    )


def _distance_to_segment_m(point: Point, start: Point, end: Point) -> float:
    reference_latitude = point[1]
    px, py = _project(point, reference_latitude)
    ax, ay = _project(start, reference_latitude)
    bx, by = _project(end, reference_latitude)
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(px - ax, py - ay)
    proportion = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    closest_x, closest_y = ax + proportion * dx, ay + proportion * dy
    return math.hypot(px - closest_x, py - closest_y)


def _inside_polygon(point: Point, ring: List[Point]) -> bool:
    longitude, latitude = point
    inside = False
    for index in range(len(ring) - 1):
        first_lon, first_lat = ring[index]
        second_lon, second_lat = ring[index + 1]
        crosses = (first_lat > latitude) != (second_lat > latitude)
        if crosses:
            edge_longitude = (
                (second_lon - first_lon) * (latitude - first_lat)
                / (second_lat - first_lat) + first_lon
            )
            if longitude < edge_longitude:
                inside = not inside
    return inside


def signed_distance_m(geometry: Dict, longitude: float, latitude: float) -> float:
    """Distância à borda: positiva dentro, negativa fora da cerca."""
    point = (float(longitude), float(latitude))
    geometry_type = str(geometry.get('type') or '').lower()
    if geometry_type == 'circle':
        center = tuple(map(float, geometry['center']))
        return float(geometry['radius_meters']) - _haversine_m(center, point)
    if geometry_type != 'polygon':
        raise ValueError('Geometria deve ser Circle ou Polygon')
    ring = [tuple(map(float, item)) for item in geometry['coordinates'][0]]
    distance = min(
        _distance_to_segment_m(point, ring[index], ring[index + 1])
        for index in range(len(ring) - 1)
    )
    return distance if _inside_polygon(point, ring) else -distance


def classify_with_hysteresis(signed_distance: float, hysteresis: float) -> Optional[str]:
    """Classifica apenas pontos fora da banda neutra ao redor da borda."""
    margin = max(0.0, float(hysteresis))
    if signed_distance >= margin:
        return 'inside'
    if signed_distance <= -margin:
        return 'outside'
    return None


def effective_hysteresis_m(hysteresis: float, accuracy_m: Optional[float]) -> float:
    """Exige que o ponto ultrapasse também seu raio declarado de incerteza."""
    return max(0.0, float(hysteresis)) + max(0.0, float(accuracy_m or 0))


def _schedule_time(value) -> datetime_time:
    if isinstance(value, datetime_time):
        return value
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86_400
        return datetime_time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
    return datetime_time.fromisoformat(str(value))


def schedule_is_active(received_at: datetime, timezone_name: str, schedules: List[Dict]) -> bool:
    """Sem janelas significa 24×7; dia 0 é segunda-feira."""
    if not schedules:
        return True
    try:
        target_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return False
    system_zone = ZoneInfo(SYSTEM_TIMEZONE)
    aware = received_at.replace(tzinfo=system_zone) if received_at.tzinfo is None else received_at
    local = aware.astimezone(target_zone)
    weekday, current_time = local.weekday(), local.time().replace(tzinfo=None)
    for schedule in schedules:
        day = int(schedule['day_of_week'])
        start = _schedule_time(schedule['start_time'])
        end = _schedule_time(schedule['end_time'])
        if schedule['crosses_midnight']:
            if (weekday == day and current_time >= start) or (
                weekday == (day + 1) % 7 and current_time < end
            ):
                return True
        elif weekday == day and start <= current_time < end:
            return True
    return False


def active_window_start(
    received_at: datetime, timezone_name: str, schedules: List[Dict],
) -> Optional[datetime]:
    """Início, no relógio do sistema, da janela semanal que está ativa agora."""
    if not schedules:
        return None
    local = _local_datetime(received_at, timezone_name)
    if local is None:
        return None
    starts = []
    weekday, current_time = local.weekday(), local.time().replace(tzinfo=None)
    for schedule in schedules:
        day = int(schedule['day_of_week'])
        start = _schedule_time(schedule['start_time'])
        end = _schedule_time(schedule['end_time'])
        start_date = None
        if schedule['crosses_midnight']:
            if weekday == day and current_time >= start:
                start_date = local.date()
            elif weekday == (day + 1) % 7 and current_time < end:
                start_date = local.date() - timedelta(days=1)
        elif weekday == day and start <= current_time < end:
            start_date = local.date()
        if start_date is not None:
            local_start = datetime.combine(start_date, start, tzinfo=local.tzinfo)
            starts.append(
                local_start.astimezone(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)
            )
    return min(starts) if starts else None


def _local_datetime(received_at: datetime, timezone_name: str) -> Optional[datetime]:
    try:
        target_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None
    system_zone = ZoneInfo(SYSTEM_TIMEZONE)
    aware = received_at.replace(tzinfo=system_zone) if received_at.tzinfo is None else received_at
    return aware.astimezone(target_zone)


def evolve_state(
    stable_state: str,
    pending_state: Optional[str],
    pending_samples: int,
    candidate_state: Optional[str],
    confirmation_samples: int = CONFIRMATION_SAMPLES,
) -> StateEvolution:
    """Aplica confirmação consecutiva; retorna transição apenas após estabilizar."""
    required = max(1, int(confirmation_samples))
    if candidate_state is None:
        return StateEvolution(stable_state, None, 0, None)
    if stable_state == 'unknown':
        return StateEvolution(candidate_state, None, 0, None)
    if candidate_state == stable_state:
        return StateEvolution(stable_state, None, 0, None)
    samples = pending_samples + 1 if pending_state == candidate_state else 1
    if samples < required:
        return StateEvolution(stable_state, candidate_state, samples, None)
    transition = (stable_state, candidate_state)
    return StateEvolution(candidate_state, None, 0, transition)


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    else:
        parsed = datetime.now()
    if parsed.tzinfo:
        parsed = parsed.astimezone(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)
    return parsed


def _resolve_subjects(cursor, source: str, identifiers: Dict, observed_at: datetime) -> Dict:
    vehicle_id = None
    driver_id = None
    if source == 'tracker':
        values = []
        clauses = []
        if identifiers.get('device_id'):
            clauses.append("(vi.tipo_identidade = 'device_id' AND vi.valor_externo = %s)")
            values.append(str(identifiers['device_id']))
        if identifiers.get('vehicle_id') is not None:
            clauses.append("(vi.tipo_identidade = 'vehicle_id' AND vi.valor_externo = %s)")
            values.append(str(identifiers['vehicle_id']))
        if clauses:
            cursor.execute(f"""
                SELECT vi.vehicle_id FROM monitoramento.veiculo_identidades vi
                 WHERE vi.fonte_codigo = 'tracker' AND vi.ativo = TRUE
                   AND ({' OR '.join(clauses)})
                 ORDER BY vi.principal DESC, vi.id LIMIT 1
            """, tuple(values))
            row = cursor.fetchone()
            vehicle_id = row['vehicle_id'] if row else None
    else:
        cursor.execute("""
            SELECT mi.driver_id FROM monitoramento.motorista_identidades mi
             WHERE mi.fonte_codigo = 'dirijabem' AND mi.tipo_identidade = 'user_id'
               AND mi.valor_externo = %s AND mi.ativo = TRUE
             ORDER BY mi.id LIMIT 1
        """, (str(identifiers['user_id']),))
        row = cursor.fetchone()
        driver_id = row['driver_id'] if row else None
        if identifiers.get('plate'):
            cursor.execute("""
                SELECT vi.vehicle_id FROM monitoramento.veiculo_identidades vi
                 WHERE vi.fonte_codigo = 'dirijabem' AND vi.tipo_identidade = 'plate'
                   AND vi.valor_externo = %s AND vi.ativo = TRUE
                 ORDER BY vi.principal DESC, vi.id LIMIT 1
            """, (str(identifiers['plate']),))
            row = cursor.fetchone()
            vehicle_id = row['vehicle_id'] if row else None

    if vehicle_id and not driver_id:
        cursor.execute("""
            SELECT driver_id FROM monitoramento.veiculo_motorista_vinculos
             WHERE vehicle_id = %s AND valido_desde <= %s
               AND (valido_ate IS NULL OR valido_ate >= %s)
             ORDER BY valido_desde DESC, id DESC LIMIT 1
        """, (vehicle_id, observed_at, observed_at))
        row = cursor.fetchone()
        driver_id = row['driver_id'] if row else None
    if driver_id and not vehicle_id:
        cursor.execute("""
            SELECT vehicle_id FROM monitoramento.veiculo_motorista_vinculos
             WHERE driver_id = %s AND valido_desde <= %s
               AND (valido_ate IS NULL OR valido_ate >= %s)
             ORDER BY valido_desde DESC, id DESC LIMIT 1
        """, (driver_id, observed_at, observed_at))
        row = cursor.fetchone()
        vehicle_id = row['vehicle_id'] if row else None
    return {'vehicle_id': vehicle_id, 'driver_id': driver_id}


def _applicable_assignments(cursor, subjects: Dict, observed_at: datetime) -> List[Dict]:
    vehicle_id, driver_id = subjects['vehicle_id'], subjects['driver_id']
    if vehicle_id is None and driver_id is None:
        return []
    cursor.execute("""
        SELECT DISTINCT ga.id AS assignment_id, ga.target_type, ga.vehicle_id,
               ga.driver_id, ga.group_id, ga.notify_on_entry, ga.notify_on_exit,
               ga.hysteresis_meters, ga.timezone_name, ga.dwell_threshold_seconds,
               ga.effective_from, ga.effective_to,
               g.id AS geofence_id, g.regra,
               gv.id AS geometry_version_id, gv.geometry_type, gv.radius_meters,
               ST_AsGeoJSON(gv.geometry) AS geometry_geojson,
               gm.vehicle_id AS group_vehicle_id, gm.driver_id AS group_driver_id,
               gs.id AS schedule_id, gs.day_of_week, gs.start_time, gs.end_time,
               gs.crosses_midnight
          FROM monitoramento.geofence_assignments ga
          JOIN monitoramento.geofences g ON g.id = ga.geofence_id
          JOIN monitoramento.geofence_versions gv ON gv.id = (
               SELECT latest.id FROM monitoramento.geofence_versions latest
                WHERE latest.geofence_id = g.id
                ORDER BY latest.version_number DESC LIMIT 1
          )
     LEFT JOIN monitoramento.monitoring_group_members gm
            ON gm.group_id = ga.group_id AND gm.ativo = TRUE
     LEFT JOIN monitoramento.geofence_assignment_schedules gs
            ON gs.assignment_id = ga.id AND gs.ativo = TRUE
         WHERE ga.ativo = TRUE AND g.status = 'active'
           AND (
             (ga.target_type = 'vehicle' AND ga.vehicle_id = %s)
             OR (ga.target_type = 'driver' AND ga.driver_id = %s)
             OR (ga.target_type = 'group' AND (
                  gm.vehicle_id = %s OR gm.driver_id = %s
             ))
           )
         ORDER BY ga.priority, ga.id
    """, (vehicle_id, driver_id, vehicle_id, driver_id))
    assignments = []
    grouped = {}
    for row in cursor.fetchall():
        grouped.setdefault(row['assignment_id'], []).append(row)
    for matching_rows in grouped.values():
        row = matching_rows[0]
        local = _local_datetime(observed_at, row['timezone_name'])
        if local is None or (
            row['effective_from'] is not None and local.date() < row['effective_from']
        ) or (
            row['effective_to'] is not None and local.date() > row['effective_to']
        ):
            continue
        if row['target_type'] == 'vehicle':
            subject_type, subject_id = 'vehicle', row['vehicle_id']
        elif row['target_type'] == 'driver':
            subject_type, subject_id = 'driver', row['driver_id']
        elif vehicle_id is not None and any(
            item['group_vehicle_id'] == vehicle_id for item in matching_rows
        ):
            subject_type, subject_id = 'vehicle', vehicle_id
        else:
            subject_type, subject_id = 'driver', driver_id
        parsed = json.loads(row['geometry_geojson'])
        if row['geometry_type'] == 'circle':
            geometry = {
                'type': 'Circle', 'center': parsed['coordinates'],
                'radius_meters': float(row['radius_meters']),
            }
        else:
            geometry = parsed
        schedules = []
        seen_schedules = set()
        for item in matching_rows:
            if item['schedule_id'] and item['schedule_id'] not in seen_schedules:
                seen_schedules.add(item['schedule_id'])
                schedules.append({
                    'day_of_week': item['day_of_week'],
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                    'crosses_midnight': bool(item['crosses_midnight']),
                })
        row.update(
            subject_type=subject_type, subject_id=subject_id,
            incident_vehicle_id=vehicle_id, incident_driver_id=driver_id,
            geometry=geometry, schedules=schedules,
        )
        assignments.append(row)
    return assignments


def _cache_key(source: str, identifiers: Dict) -> Tuple:
    return source, tuple(sorted(
        (key, str(value)) for key, value in identifiers.items() if value is not None
    ))


def _cached_assignments(source: str, identifiers: Dict) -> Optional[List[Dict]]:
    key = _cache_key(source, identifiers)
    now = time.monotonic()
    with _cache_lock:
        cached = _assignment_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        _assignment_cache.pop(key, None)
    return None


def _remember_assignments(source: str, identifiers: Dict, assignments: List[Dict]) -> None:
    with _cache_lock:
        _assignment_cache[_cache_key(source, identifiers)] = (
            time.monotonic() + CACHE_TTL_SECONDS,
            assignments,
        )


def clear_assignment_cache() -> None:
    """Invalida políticas após mutações operacionais de atribuição/agenda."""
    with _cache_lock:
        _assignment_cache.clear()


def _state_clause(assignment: Dict) -> Tuple[str, Tuple]:
    column = 'vehicle_id' if assignment['subject_type'] == 'vehicle' else 'driver_id'
    return f'assignment_id = %s AND {column} = %s', (
        assignment['assignment_id'], assignment['subject_id'],
    )


def _store_observation(
    cursor,
    assignment: Dict,
    source: str,
    longitude: float,
    latitude: float,
    accuracy_m: Optional[float],
    observed_at: datetime,
    received_at: datetime,
) -> Optional[Dict]:
    clause, params = _state_clause(assignment)
    vehicle_id = assignment['subject_id'] if assignment['subject_type'] == 'vehicle' else None
    driver_id = assignment['subject_id'] if assignment['subject_type'] == 'driver' else None
    # O upsert cria a linha sentinela antes do lock. Duas primeiras posições
    # concorrentes passam a serializar na mesma linha, sem perder uma amostra.
    cursor.execute("""
        INSERT INTO monitoramento.geofence_target_states
            (assignment_id, subject_type, vehicle_id, driver_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE id = id
    """, (
        assignment['assignment_id'], assignment['subject_type'], vehicle_id, driver_id,
    ))
    cursor.execute(
        f'SELECT * FROM monitoramento.geofence_target_states WHERE {clause} FOR UPDATE',
        params,
    )
    current = cursor.fetchone()
    if current['last_observed_at'] and received_at <= current['last_observed_at']:
        return None
    distance = signed_distance_m(assignment['geometry'], longitude, latitude)
    effective_hysteresis = effective_hysteresis_m(
        assignment['hysteresis_meters'], accuracy_m,
    )
    candidate = classify_with_hysteresis(distance, effective_hysteresis)
    evolution = evolve_state(
        current['stable_state'], current['pending_state'], int(current['pending_samples']),
        candidate,
    )
    active_now = schedule_is_active(
        received_at, assignment['timezone_name'], assignment['schedules'],
    )
    window_start = active_window_start(
        received_at, assignment['timezone_name'], assignment['schedules'],
    )
    violation_state = 'inside' if assignment['regra'] == 'forbidden' else 'outside'
    was_violation = current['stable_state'] == violation_state
    is_violation = evolution.stable_state == violation_state
    if active_now and is_violation:
        previous_start = current['violation_started_at']
        same_window = window_start is None or (
            previous_start is not None and previous_start >= window_start
        )
        violation_started_at = (
            previous_start if was_violation and previous_start and same_window else received_at
        )
        dwell_notified_at = (
            current['dwell_notified_at'] if was_violation and same_window else None
        )
        violation_episode_id = (
            current.get('violation_episode_id')
            if was_violation and same_window and current.get('violation_episode_id')
            else str(uuid5(
                NAMESPACE_URL,
                f"aitrack:geofence-episode:{assignment['assignment_id']}:"
                f"{assignment['subject_type']}:{assignment['subject_id']}:"
                f"{violation_started_at.isoformat(timespec='microseconds')}",
            ))
        )
    else:
        violation_started_at = None
        dwell_notified_at = None
        violation_episode_id = None
    event_episode_id = (
        violation_episode_id or current.get('violation_episode_id') or str(uuid5(
            NAMESPACE_URL,
            f"aitrack:geofence-episode:{assignment['assignment_id']}:"
            f"{assignment['subject_type']}:{assignment['subject_id']}:"
            f"{received_at.isoformat(timespec='microseconds')}",
        ))
    )
    transition_at = received_at if evolution.transition else (
        current['last_transition_at']
    )

    event_type = None
    crossing_direction = None
    if evolution.transition and active_now:
        candidate_event = (
            'geofence_entry' if evolution.transition == ('outside', 'inside')
            else 'geofence_exit'
        )
        should_notify = (
            candidate_event == 'geofence_entry' and assignment['notify_on_entry']
        ) or (
            candidate_event == 'geofence_exit' and assignment['notify_on_exit']
        )
        if should_notify:
            event_type = candidate_event
            crossing_direction = '_to_'.join(evolution.transition)
    threshold = assignment['dwell_threshold_seconds']
    dwell_due = bool(
        active_now and is_violation and threshold is not None
        and dwell_notified_at is None and violation_started_at is not None
        and (received_at - violation_started_at).total_seconds() >= int(threshold)
    )
    if dwell_due and event_type is None:
        event_type = 'geofence_dwell'
        dwell_notified_at = received_at

    cursor.execute("""
        UPDATE monitoramento.geofence_target_states
           SET stable_state = %s, pending_state = %s, pending_samples = %s,
               last_signed_distance_m = %s, last_latitude = %s,
               last_longitude = %s, last_accuracy_m = %s, last_source = %s,
               last_observed_at = %s, last_transition_at = %s,
               violation_started_at = %s, dwell_notified_at = %s,
               violation_episode_id = %s,
               version = version + 1
         WHERE id = %s
    """, (
        evolution.stable_state, evolution.pending_state, evolution.pending_samples,
        distance, latitude, longitude, accuracy_m, source, received_at,
        transition_at, violation_started_at, dwell_notified_at,
        violation_episode_id, current['id'],
    ))
    if event_type is None:
        return None
    public_id = str(uuid5(
        NAMESPACE_URL,
        f"aitrack:geofence:{assignment['assignment_id']}:{assignment['subject_type']}:"
        f"{assignment['subject_id']}:{event_type}:{received_at.isoformat(timespec='microseconds')}",
    ))
    context_vehicle_id = assignment['incident_vehicle_id']
    if assignment['subject_type'] == 'driver':
        cursor.execute("""
            SELECT vehicle_id
              FROM monitoramento.veiculo_motorista_vinculos
             WHERE driver_id = %s AND valido_desde <= %s
               AND (valido_ate IS NULL OR valido_ate >= %s)
             ORDER BY valido_desde DESC, id DESC LIMIT 2
        """, (assignment['subject_id'], observed_at, observed_at))
        linked_vehicles = cursor.fetchall()
        resolved_from_position = assignment['incident_vehicle_id']
        matching_position = next((
            row['vehicle_id'] for row in linked_vehicles
            if row['vehicle_id'] == resolved_from_position
        ), None)
        context_vehicle_id = matching_position if matching_position is not None else (
            linked_vehicles[0]['vehicle_id'] if len(linked_vehicles) == 1 else None
        )
    cursor.execute("""
        INSERT INTO monitoramento.geofence_events
            (public_id, assignment_id, geofence_id, geometry_version_id,
             violation_episode_id, context_vehicle_id, correlation_status,
             source_code, event_type, crossing_direction, rule_applied,
             subject_type, vehicle_id, driver_id, latitude, longitude,
             accuracy_m, signed_distance_m, observed_at, received_at, details_json)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        public_id, assignment['assignment_id'], assignment['geofence_id'],
        assignment['geometry_version_id'], event_episode_id,
        context_vehicle_id, source, event_type,
        crossing_direction, assignment['regra'], assignment['subject_type'],
        vehicle_id, driver_id, latitude, longitude, accuracy_m, distance,
        observed_at, received_at, json.dumps({
            'confirmation_samples': CONFIRMATION_SAMPLES,
            'hysteresis_meters': float(assignment['hysteresis_meters']),
            'effective_hysteresis_meters': effective_hysteresis,
            'schedule_active': active_now,
            'timezone_name': assignment['timezone_name'],
            'dwell_threshold_seconds': int(threshold) if threshold is not None else None,
            'violation_started_at': (
                violation_started_at.isoformat() if violation_started_at else None
            ),
            'violation_episode_id': event_episode_id,
        }),
    ))
    geofence_event_id = cursor.lastrowid
    incident_payload = {
        'geofence_event_id': geofence_event_id,
        'public_id': public_id,
        'vehicle_id': context_vehicle_id,
        'driver_id': assignment['incident_driver_id'],
        'assignment_id': assignment['assignment_id'],
        'geofence_id': assignment['geofence_id'],
        'geometry_version_id': assignment['geometry_version_id'],
        'source': source,
        'event_type': event_type,
        'crossing_direction': crossing_direction,
        'rule_applied': assignment['regra'],
        'subject_type': assignment['subject_type'],
        'latitude': latitude,
        'longitude': longitude,
        'observed_at': observed_at,
        'violation_episode_id': event_episode_id,
    }
    cursor.execute('SAVEPOINT correlate_geofence_event')
    try:
        incident = correlate_geofence_event(cursor, incident_payload)
        cursor.execute('RELEASE SAVEPOINT correlate_geofence_event')
    except Exception as error:
        cursor.execute('ROLLBACK TO SAVEPOINT correlate_geofence_event')
        cursor.execute("""
            UPDATE monitoramento.geofence_events
               SET correlation_status = 'error',
                   correlation_attempts = correlation_attempts + 1,
                   correlation_error = %s
             WHERE id = %s
        """, (str(error)[:1000], geofence_event_id))
        LOGGER.exception(
            'Evento de cerca %s persistido; correlação será retomada', public_id,
        )
        incident = {'status': 'error', 'reason': str(error)}
    if incident['status'] == 'ignored':
        deferred = incident['reason'] == 'vehicle_identity_not_found'
        cursor.execute("""
            UPDATE monitoramento.geofence_events
               SET correlation_status = %s,
                   correlation_attempts = correlation_attempts + 1,
                   correlation_error = %s,
                   next_correlation_at = CASE
                       WHEN %s THEN CURRENT_TIMESTAMP(6) + INTERVAL 1 HOUR
                       ELSE NULL END
             WHERE id = %s
        """, (
            'deferred' if deferred else 'ignored', incident['reason'][:1000],
            deferred, geofence_event_id,
        ))
        LOGGER.warning(
            'Evento de cerca %s sem veículo canônico; incidente não criado', public_id,
        )
    if incident['status'] != 'correlated':
        return {
            'public_id': public_id,
            'event_type': event_type,
            'crossing_direction': crossing_direction,
            'assignment_id': assignment['assignment_id'],
            'geofence_id': assignment['geofence_id'],
            'incident_id': None,
            'incident_created': False,
            'evidence_added': False,
        }
    return {
        'public_id': public_id,
        'event_type': event_type,
        'crossing_direction': crossing_direction,
        'assignment_id': assignment['assignment_id'],
        'geofence_id': assignment['geofence_id'],
        'incident_id': incident['incident_id'],
        'incident_created': incident['incident_created'],
        'evidence_added': incident['evidence_added'],
    }


def evaluate_position(
    source: str,
    identifiers: Dict,
    longitude: float,
    latitude: float,
    observed_at=None,
    accuracy_m: Optional[float] = None,
    received_at=None,
    external_position_id=None,
) -> List[Dict]:
    """Resolve identidades canônicas e persiste transições confirmadas."""
    if source not in {'tracker', 'dirijabem'}:
        raise ValueError('Fonte deve ser tracker ou dirijabem')
    timestamp = _as_datetime(observed_at)
    reception_timestamp = _as_datetime(received_at)
    assignments = _cached_assignments(source, identifiers)
    if assignments == []:
        return []
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        if assignments is None:
            subjects = _resolve_subjects(cursor, source, identifiers, reception_timestamp)
            assignments = _applicable_assignments(cursor, subjects, reception_timestamp)
            _remember_assignments(source, identifiers, assignments)
        if not assignments:
            conn.commit()
            return []
        if external_position_id is not None:
            cursor.execute("""
                INSERT INTO monitoramento.source_position_receipts
                    (source_code, external_position_id, received_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE external_position_id = external_position_id
            """, (source, str(external_position_id), reception_timestamp))
            if cursor.rowcount == 0:
                conn.commit()
                return []
        events = []
        for assignment in assignments:
            event = _store_observation(
                cursor, assignment, source, float(longitude), float(latitude),
                float(accuracy_m) if accuracy_m is not None else None, timestamp,
                reception_timestamp,
            )
            if event:
                events.append(event)
        conn.commit()
        return events
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def evaluate_tracker_position(
    device_id, vehicle_id, longitude, latitude, observed_at=None, accuracy_m=None,
    received_at=None, external_position_id=None,
) -> List[Dict]:
    return evaluate_position(
        'tracker', {'device_id': device_id, 'vehicle_id': vehicle_id},
        longitude, latitude, observed_at, accuracy_m, received_at, external_position_id,
    )


def evaluate_dirijabem_position(
    user_id, longitude, latitude, observed_at=None, plate=None, accuracy_m=None,
    received_at=None, external_position_id=None,
) -> List[Dict]:
    return evaluate_position(
        'dirijabem', {'user_id': user_id, 'plate': plate},
        longitude, latitude, observed_at, accuracy_m, received_at, external_position_id,
    )
