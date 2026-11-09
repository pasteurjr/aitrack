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
from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional, Tuple
from uuid import NAMESPACE_URL, uuid5

from .monitor_db import get_connection


LOGGER = logging.getLogger(__name__)
EARTH_RADIUS_M = 6_371_008.8
CONFIRMATION_SAMPLES = max(1, int(os.getenv('GEOFENCE_CONFIRMATION_SAMPLES', '2')))
CACHE_TTL_SECONDS = max(1, int(os.getenv('GEOFENCE_CACHE_TTL_SECONDS', '60')))
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
        parsed = parsed.astimezone().replace(tzinfo=None)
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
               ga.hysteresis_meters, g.id AS geofence_id, g.regra,
               gv.id AS geometry_version_id, gv.geometry_type, gv.radius_meters,
               ST_AsGeoJSON(gv.geometry) AS geometry_geojson,
               gm.vehicle_id AS group_vehicle_id, gm.driver_id AS group_driver_id
          FROM monitoramento.geofence_assignments ga
          JOIN monitoramento.geofences g ON g.id = ga.geofence_id
          JOIN monitoramento.geofence_versions gv ON gv.id = (
               SELECT latest.id FROM monitoramento.geofence_versions latest
                WHERE latest.geofence_id = g.id
                ORDER BY latest.version_number DESC LIMIT 1
          )
     LEFT JOIN monitoramento.monitoring_group_members gm
            ON gm.group_id = ga.group_id AND gm.ativo = TRUE
         WHERE ga.ativo = TRUE AND g.status = 'active'
           AND (ga.effective_from IS NULL OR ga.effective_from <= DATE(%s))
           AND (ga.effective_to IS NULL OR ga.effective_to >= DATE(%s))
           AND (
             (ga.target_type = 'vehicle' AND ga.vehicle_id = %s)
             OR (ga.target_type = 'driver' AND ga.driver_id = %s)
             OR (ga.target_type = 'group' AND (
                  gm.vehicle_id = %s OR gm.driver_id = %s
             ))
           )
         ORDER BY ga.priority, ga.id
    """, (observed_at, observed_at, vehicle_id, driver_id, vehicle_id, driver_id))
    assignments = []
    seen = set()
    for row in cursor.fetchall():
        if row['assignment_id'] in seen:
            continue
        seen.add(row['assignment_id'])
        if row['target_type'] == 'vehicle':
            subject_type, subject_id = 'vehicle', row['vehicle_id']
        elif row['target_type'] == 'driver':
            subject_type, subject_id = 'driver', row['driver_id']
        elif row['group_vehicle_id'] == vehicle_id and vehicle_id is not None:
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
        row.update(subject_type=subject_type, subject_id=subject_id, geometry=geometry)
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
) -> Optional[Dict]:
    clause, params = _state_clause(assignment)
    cursor.execute(
        f'SELECT * FROM monitoramento.geofence_target_states WHERE {clause} FOR UPDATE',
        params,
    )
    current = cursor.fetchone()
    if current and current['last_observed_at'] and observed_at <= current['last_observed_at']:
        return None
    distance = signed_distance_m(assignment['geometry'], longitude, latitude)
    candidate = classify_with_hysteresis(distance, float(assignment['hysteresis_meters']))
    evolution = evolve_state(
        current['stable_state'] if current else 'unknown',
        current['pending_state'] if current else None,
        int(current['pending_samples']) if current else 0,
        candidate,
    )
    vehicle_id = assignment['subject_id'] if assignment['subject_type'] == 'vehicle' else None
    driver_id = assignment['subject_id'] if assignment['subject_type'] == 'driver' else None
    transition_at = observed_at if evolution.transition else (
        current['last_transition_at'] if current else None
    )
    if current:
        cursor.execute("""
            UPDATE monitoramento.geofence_target_states
               SET stable_state = %s, pending_state = %s, pending_samples = %s,
                   last_signed_distance_m = %s, last_latitude = %s,
                   last_longitude = %s, last_accuracy_m = %s, last_source = %s,
                   last_observed_at = %s, last_transition_at = %s,
                   version = version + 1
             WHERE id = %s
        """, (
            evolution.stable_state, evolution.pending_state, evolution.pending_samples,
            distance, latitude, longitude, accuracy_m, source, observed_at,
            transition_at, current['id'],
        ))
    else:
        cursor.execute("""
            INSERT INTO monitoramento.geofence_target_states
                (assignment_id, subject_type, vehicle_id, driver_id, stable_state,
                 pending_state, pending_samples, last_signed_distance_m,
                 last_latitude, last_longitude, last_accuracy_m, last_source,
                 last_observed_at, last_transition_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            assignment['assignment_id'], assignment['subject_type'], vehicle_id,
            driver_id, evolution.stable_state, evolution.pending_state,
            evolution.pending_samples, distance, latitude, longitude, accuracy_m,
            source, observed_at, transition_at,
        ))
    if not evolution.transition:
        return None
    event_type = 'geofence_entry' if evolution.transition == ('outside', 'inside') else 'geofence_exit'
    crossing_direction = '_to_'.join(evolution.transition)
    should_notify = (
        event_type == 'geofence_entry' and assignment['notify_on_entry']
    ) or (
        event_type == 'geofence_exit' and assignment['notify_on_exit']
    )
    if not should_notify:
        return None
    public_id = str(uuid5(
        NAMESPACE_URL,
        f"aitrack:geofence:{assignment['assignment_id']}:{assignment['subject_type']}:"
        f"{assignment['subject_id']}:{event_type}:{observed_at.isoformat(timespec='microseconds')}",
    ))
    cursor.execute("""
        INSERT IGNORE INTO monitoramento.geofence_events
            (public_id, assignment_id, geofence_id, geometry_version_id,
             source_code, event_type, crossing_direction, rule_applied,
             subject_type, vehicle_id, driver_id, latitude, longitude,
             accuracy_m, signed_distance_m, observed_at, details_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s)
    """, (
        public_id, assignment['assignment_id'], assignment['geofence_id'],
        assignment['geometry_version_id'], source, event_type,
        crossing_direction, assignment['regra'], assignment['subject_type'],
        vehicle_id, driver_id, latitude, longitude, accuracy_m, distance,
        observed_at, json.dumps({
            'confirmation_samples': CONFIRMATION_SAMPLES,
            'hysteresis_meters': float(assignment['hysteresis_meters']),
        }),
    ))
    return {
        'public_id': public_id,
        'event_type': event_type,
        'crossing_direction': crossing_direction,
        'assignment_id': assignment['assignment_id'],
        'geofence_id': assignment['geofence_id'],
    }


def evaluate_position(
    source: str,
    identifiers: Dict,
    longitude: float,
    latitude: float,
    observed_at=None,
    accuracy_m: Optional[float] = None,
) -> List[Dict]:
    """Resolve identidades canônicas e persiste transições confirmadas."""
    if source not in {'tracker', 'dirijabem'}:
        raise ValueError('Fonte deve ser tracker ou dirijabem')
    timestamp = _as_datetime(observed_at)
    assignments = _cached_assignments(source, identifiers)
    if assignments == []:
        return []
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        if assignments is None:
            subjects = _resolve_subjects(cursor, source, identifiers, timestamp)
            assignments = _applicable_assignments(cursor, subjects, timestamp)
            _remember_assignments(source, identifiers, assignments)
        if not assignments:
            conn.commit()
            return []
        events = []
        for assignment in assignments:
            event = _store_observation(
                cursor, assignment, source, float(longitude), float(latitude),
                float(accuracy_m) if accuracy_m is not None else None, timestamp,
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
) -> List[Dict]:
    return evaluate_position(
        'tracker', {'device_id': device_id, 'vehicle_id': vehicle_id},
        longitude, latitude, observed_at, accuracy_m,
    )


def evaluate_dirijabem_position(
    user_id, longitude, latitude, observed_at=None, plate=None, accuracy_m=None,
) -> List[Dict]:
    return evaluate_position(
        'dirijabem', {'user_id': user_id, 'plate': plate},
        longitude, latitude, observed_at, accuracy_m,
    )
