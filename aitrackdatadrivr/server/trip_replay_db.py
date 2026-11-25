"""Consulta limitada do replay de uma execução de rota."""

import json
from decimal import Decimal

from .monitor_db import get_connection
from .trip_replay import merge_timeline, serialize_event


MAX_POSITIONS = 5000


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def get_trip_replay(execution_public_id, position_limit=MAX_POSITIONS, connection=None):
    if not isinstance(position_limit, int) or not 1 <= position_limit <= MAX_POSITIONS:
        raise ValueError(f'position_limit deve estar entre 1 e {MAX_POSITIONS}')

    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT e.id, e.public_id, e.status, e.planned_start_at,
                      e.planned_end_at, e.started_at, e.completed_at,
                      v.geometry_json, v.corridor_meters, v.version_no
                 FROM monitoramento.route_executions e
                 JOIN monitoramento.route_versions v ON v.id=e.route_version_id
                WHERE e.public_id=%s""",
            (execution_public_id,),
        )
        execution = cursor.fetchone()
        if not execution:
            raise LookupError('Execução de rota não encontrada')

        cursor.execute(
            """SELECT id, source, external_position_id, observed_at,
                      longitude, latitude, speed_kmh, distance_meters
                 FROM monitoramento.route_position_receipts
                WHERE execution_id=%s AND longitude IS NOT NULL AND latitude IS NOT NULL
                ORDER BY observed_at, id LIMIT %s""",
            (execution['id'], position_limit),
        )
        positions = cursor.fetchall()
        position_events = [
            {
                'kind': 'position',
                'stable_id': f"position:{row['id']}",
                'occurred_at': row['observed_at'],
                'source': row['source'],
                'external_position_id': row['external_position_id'],
                'longitude': row['longitude'],
                'latitude': row['latitude'],
                'speed_kmh': _number(row['speed_kmh']),
                'distance_meters': _number(row['distance_meters']),
            }
            for row in positions
        ]

        cursor.execute(
            """SELECT id, episode_type, status, started_at, ended_at,
                      max_distance_meters
                 FROM monitoramento.route_episodes
                WHERE execution_id=%s
                ORDER BY started_at, id""",
            (execution['id'],),
        )
        episode_events = []
        for episode in cursor.fetchall():
            common = {
                'episode_type': episode['episode_type'],
                'max_distance_meters': _number(episode['max_distance_meters']),
            }
            episode_events.append({
                **common,
                'kind': 'episode_started',
                'stable_id': f"episode:{episode['id']}:started",
                'occurred_at': episode['started_at'],
            })
            if episode['ended_at']:
                episode_events.append({
                    **common,
                    'kind': 'episode_recovered',
                    'stable_id': f"episode:{episode['id']}:recovered",
                    'occurred_at': episode['ended_at'],
                })

        cursor.execute(
            """SELECT id, event_type, from_status, to_status, actor_id, occurred_at
                 FROM monitoramento.route_execution_timeline
                WHERE execution_id=%s ORDER BY occurred_at, id""",
            (execution['id'],),
        )
        execution_events = [
            {
                'kind': 'execution',
                'stable_id': f"execution:{row['id']}",
                'occurred_at': row['occurred_at'],
                'event_type': row['event_type'],
                'from_status': row['from_status'],
                'to_status': row['to_status'],
                'actor_id': row['actor_id'],
            }
            for row in cursor.fetchall()
        ]

        timeline = merge_timeline(execution_events, position_events, episode_events)
        geometry = json.loads(execution['geometry_json'])
        return {
            'schema_version': 'trip-replay.v1',
            'mode': 'replay',
            'read_only': True,
            'execution': {
                'public_id': execution['public_id'],
                'status': execution['status'],
                'planned_start_at': execution['planned_start_at'].isoformat(),
                'planned_end_at': execution['planned_end_at'].isoformat(),
                'started_at': execution['started_at'].isoformat() if execution['started_at'] else None,
                'completed_at': execution['completed_at'].isoformat() if execution['completed_at'] else None,
                'route_version': execution['version_no'],
            },
            'planned_route': {
                'geometry': geometry,
                'corridor_meters': _number(execution['corridor_meters']),
            },
            'positions': [serialize_event(event) for event in position_events],
            'timeline': [serialize_event(event) for event in timeline],
            'truncated': len(positions) == position_limit,
            'position_limit': position_limit,
        }
    finally:
        cursor.close()
        if owns_connection:
            conn.close()
