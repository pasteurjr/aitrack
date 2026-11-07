"""Prova opt-in do backfill de incidente contra o MariaDB compartilhado."""

import importlib.util
import os
from pathlib import Path
import uuid

import pytest

from server.monitor_db import get_connection


BACKFILL_PATH = (
    Path(__file__).resolve().parents[2]
    / 'migrations'
    / 'backfill_operational_incidents.py'
)
SPEC = importlib.util.spec_from_file_location('incident_backfill_integration', BACKFILL_PATH)
backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill)

pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)


def test_backfill_preserves_id_timeline_monitor_and_maps_canonical_vehicle():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    incident_id = None
    try:
        cursor.execute("""
            SELECT vu.id AS legacy_id, vi.vehicle_id
              FROM tracker.veiculo_unificado vu
              JOIN monitoramento.veiculo_identidades vi
                ON vi.fonte_codigo = 'tracker'
               AND vi.tipo_identidade = 'device_id'
               AND vi.valor_externo = vu.device_id
             WHERE vu.ativo = TRUE AND vu.device_id IS NOT NULL
             ORDER BY vu.id
             LIMIT 1
        """)
        identity = cursor.fetchone()
        if not identity:
            pytest.skip('identidade Tracker canônica indisponível')
        token = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO tracker.incidents
                (correlation_key, vehicle_id, monitor_id, incident_type, title,
                 status, severity, primary_source, version)
            VALUES (%s, %s, 1, 'migration_test', 'Teste UI-3.0E1', 'new',
                    'low', 'tracker', 1)
        """, (f'ui30e1:{token}', identity['legacy_id']))
        incident_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO tracker.incident_timeline
                (incident_id, idempotency_key, entry_type, actor_type, summary,
                 occurred_at)
            VALUES (%s, %s, 'evidence_added', 'integration',
                    'Evidência temporária UI-3.0E1', CURRENT_TIMESTAMP(6))
        """, (incident_id, f'ui30e1:{token}:timeline'))
        conn.commit()

        backfill.apply_backfill(conn)

        cursor.execute("""
            SELECT id, vehicle_id, legacy_vehicle_id, monitor_id
              FROM monitoramento.incidents WHERE id = %s
        """, (incident_id,))
        copied = cursor.fetchone()
        assert copied == {
            'id': incident_id,
            'vehicle_id': identity['vehicle_id'],
            'legacy_vehicle_id': identity['legacy_id'],
            'monitor_id': 1,
        }
        cursor.execute("""
            SELECT incident_id, idempotency_key
              FROM monitoramento.incident_timeline WHERE incident_id = %s
        """, (incident_id,))
        timeline = cursor.fetchone()
        assert timeline == {
            'incident_id': incident_id,
            'idempotency_key': f'ui30e1:{token}:timeline',
        }
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
            cursor.execute(
                'DELETE FROM tracker.incident_timeline WHERE incident_id = %s',
                (incident_id,),
            )
            cursor.execute('DELETE FROM tracker.incidents WHERE id = %s', (incident_id,))
            conn.commit()
        cursor.close()
        conn.close()
