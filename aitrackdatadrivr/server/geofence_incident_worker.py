"""Retoma correlações de cerca que falharam após o evento ser confirmado."""

import logging
import os
import time

from .incident_correlator import correlate_geofence_event
from .monitor_db import get_connection


LOGGER = logging.getLogger(__name__)
POLL_SECONDS = max(0.5, float(os.getenv('GEOFENCE_INCIDENT_POLL_SECONDS', '5')))
BATCH_SIZE = max(1, min(500, int(os.getenv('GEOFENCE_INCIDENT_BATCH_SIZE', '100'))))
MAX_ATTEMPTS = max(1, int(os.getenv('GEOFENCE_INCIDENT_MAX_ATTEMPTS', '10')))
DEFERRED_RETRY_HOURS = max(
    1, int(os.getenv('GEOFENCE_INCIDENT_DEFERRED_RETRY_HOURS', '1')),
)


def _payload(row):
    return {
        'geofence_event_id': row['id'],
        'public_id': row['public_id'],
        'vehicle_id': row['context_vehicle_id'],
        'driver_id': row['driver_id'],
        'assignment_id': row['assignment_id'],
        'geofence_id': row['geofence_id'],
        'geometry_version_id': row['geometry_version_id'],
        'source': row['source_code'],
        'event_type': row['event_type'],
        'crossing_direction': row['crossing_direction'],
        'rule_applied': row['rule_applied'],
        'subject_type': row['subject_type'],
        'latitude': row['latitude'],
        'longitude': row['longitude'],
        'observed_at': row['observed_at'],
        'violation_episode_id': row['violation_episode_id'],
    }


def process_pending_once(limit=BATCH_SIZE) -> int:
    """Processa um lote com savepoint por evento e retorna sucessos."""
    limit = max(1, min(500, int(limit)))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    correlated = 0
    try:
        conn.start_transaction()
        cursor.execute("""
            SELECT id, public_id, assignment_id, geofence_id,
                   geometry_version_id, violation_episode_id,
                   context_vehicle_id, source_code, event_type,
                   crossing_direction, rule_applied, subject_type,
                   driver_id, latitude, longitude, observed_at
              FROM monitoramento.geofence_events
             WHERE (
                    correlation_status = 'pending'
                    OR (correlation_status = 'error' AND correlation_attempts < %s)
                    OR (correlation_status = 'deferred'
                        AND next_correlation_at <= CURRENT_TIMESTAMP(6))
                   )
               AND violation_episode_id IS NOT NULL
             ORDER BY received_at, id
             LIMIT %s
             FOR UPDATE
        """, (MAX_ATTEMPTS, limit))
        rows = cursor.fetchall()
        for row in rows:
            cursor.execute('SAVEPOINT retry_geofence_incident')
            try:
                if row['context_vehicle_id'] is None and row['driver_id'] is not None:
                    cursor.execute("""
                        SELECT vehicle_id
                          FROM monitoramento.veiculo_motorista_vinculos
                         WHERE driver_id = %s AND valido_desde <= %s
                           AND (valido_ate IS NULL OR valido_ate >= %s)
                         ORDER BY valido_desde DESC, id DESC LIMIT 2
                    """, (row['driver_id'], row['observed_at'], row['observed_at']))
                    links = cursor.fetchall()
                    if len(links) == 1:
                        row['context_vehicle_id'] = links[0]['vehicle_id']
                        cursor.execute(
                            'UPDATE monitoramento.geofence_events '
                            'SET context_vehicle_id = %s WHERE id = %s',
                            (row['context_vehicle_id'], row['id']),
                        )
                result = correlate_geofence_event(cursor, _payload(row))
                if result['status'] == 'ignored':
                    deferred = result['reason'] == 'vehicle_identity_not_found'
                    cursor.execute("""
                        UPDATE monitoramento.geofence_events
                           SET correlation_status = %s,
                               correlation_attempts = correlation_attempts + 1,
                               correlation_error = %s,
                               next_correlation_at = CASE
                                   WHEN %s THEN CURRENT_TIMESTAMP(6)
                                     + INTERVAL %s HOUR
                                   ELSE NULL END
                         WHERE id = %s
                    """, (
                        'deferred' if deferred else 'ignored',
                        result['reason'][:1000], deferred,
                        DEFERRED_RETRY_HOURS, row['id'],
                    ))
                else:
                    correlated += 1
                cursor.execute('RELEASE SAVEPOINT retry_geofence_incident')
            except Exception as error:
                cursor.execute('ROLLBACK TO SAVEPOINT retry_geofence_incident')
                cursor.execute("""
                    UPDATE monitoramento.geofence_events
                       SET correlation_status = 'error',
                           correlation_attempts = correlation_attempts + 1,
                           correlation_error = %s
                     WHERE id = %s
                """, (str(error)[:1000], row['id']))
                LOGGER.exception('Falha ao retomar evento de cerca %s', row['public_id'])
        conn.commit()
        return correlated
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def run_forever() -> None:
    LOGGER.info('Worker de incidentes de cerca iniciado')
    while True:
        try:
            if process_pending_once() >= BATCH_SIZE:
                continue
        except Exception:
            LOGGER.exception('Falha no worker de incidentes de cerca; nova tentativa agendada')
        time.sleep(POLL_SECONDS)
