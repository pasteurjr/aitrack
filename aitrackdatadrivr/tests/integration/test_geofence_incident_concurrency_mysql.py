"""Idempotência concorrente da correlação de cerca no MariaDB real."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4

import pytest

from server.incident_correlator import correlate_geofence_event
from server.monitor_db import get_connection


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)


def _correlate(payload, barrier):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        barrier.wait(timeout=10)
        conn.start_transaction()
        result = correlate_geofence_event(cursor, payload)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def test_same_geofence_evidence_is_correlated_once_under_concurrency():
    probe = get_connection()
    cursor = probe.cursor(dictionary=True)
    incident_id = None
    try:
        cursor.execute(
            'SELECT id FROM monitoramento.veiculos '
            'WHERE ativo = TRUE AND merged_into_id IS NULL ORDER BY id LIMIT 1'
        )
        vehicle = cursor.fetchone()
        if not vehicle:
            pytest.skip('nenhum veículo canônico ativo disponível')
        probe.commit()  # encerra o snapshot antes das transações concorrentes
        episode_id = str(uuid4())
        public_id = str(uuid4())
        payload = {
            'public_id': public_id,
            'vehicle_id': vehicle['id'],
            'driver_id': None,
            'assignment_id': 9_000_000,
            'geofence_id': 9_000_001,
            'geometry_version_id': 9_000_002,
            'source': 'tracker',
            'event_type': 'geofence_exit',
            'crossing_direction': 'inside_to_outside',
            'rule_applied': 'allowed',
            'subject_type': 'vehicle',
            'latitude': -23.5505,
            'longitude': -46.6333,
            'observed_at': datetime.now(),
            'violation_episode_id': episode_id,
        }
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [
                future.result(timeout=20)
                for future in (
                    executor.submit(_correlate, payload, barrier),
                    executor.submit(_correlate, payload, barrier),
                )
            ]

        probe.commit()  # a leitura abaixo precisa enxergar os commits dos workers
        assert sorted(result['evidence_added'] for result in results) == [False, True]
        assert len({result['incident_id'] for result in results}) == 1
        incident_id = results[0]['incident_id']
        cursor.execute(
            'SELECT event_count, version, severity FROM monitoramento.incidents '
            'WHERE id = %s',
            (incident_id,),
        )
        assert cursor.fetchone() == {
            'event_count': 1, 'version': 2, 'severity': 'critical',
        }
        cursor.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.incident_timeline '
            'WHERE incident_id = %s AND evidence_type = %s',
            (incident_id, 'geofence_event'),
        )
        assert cursor.fetchone()['total'] == 1
    finally:
        if incident_id is not None:
            cursor.execute(
                'DELETE FROM monitoramento.incident_timeline WHERE incident_id = %s',
                (incident_id,),
            )
            cursor.execute(
                'DELETE FROM monitoramento.incidents WHERE id = %s',
                (incident_id,),
            )
            probe.commit()
        cursor.close()
        probe.close()
