"""Prova opt-in de alvos, análises e alertas no MariaDB compartilhado."""

import importlib.util
import os
from pathlib import Path

import pytest

from server.monitor_db import get_connection


BACKFILL_PATH = (
    Path(__file__).resolve().parents[2]
    / 'migrations'
    / 'backfill_operational_monitors.py'
)
SPEC = importlib.util.spec_from_file_location('monitor_backfill_integration', BACKFILL_PATH)
backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill)

pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)


def test_backfill_maps_target_and_preserves_real_analysis_and_alert():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    analysis_id = None
    alert_id = None
    try:
        cursor.execute("""
            SELECT vm.id, vm.monitor_id, mt.vehicle_id
              FROM tracker.veiculomonitor vm
              JOIN monitoramento.monitor_targets mt
                ON mt.legacy_veiculomonitor_id = vm.id
             WHERE vm.ativo = TRUE
             ORDER BY vm.id
             LIMIT 1
        """)
        assignment = cursor.fetchone()
        if not assignment:
            pytest.skip('atribuição canônica indisponível')
        cursor.execute("""
            INSERT INTO tracker.monitor_analises
                (monitor_id, veiculomonitor_id, periodo_inicio, periodo_fim,
                 total_eventos, conclusao, severidade)
            VALUES (%s, %s, NOW() - INTERVAL 5 MINUTE, NOW(), 1,
                    'Análise temporária UI-3.0E2', 'low')
        """, (assignment['monitor_id'], assignment['id']))
        analysis_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO tracker.monitor_alertas
                (analise_id, monitor_id, veiculomonitor_id, titulo,
                 mensagem, severidade, tipo, status)
            VALUES (%s, %s, %s, 'Alerta temporário UI-3.0E2',
                    'Removido automaticamente', 'low', 'behavior', 'pending')
        """, (analysis_id, assignment['monitor_id'], assignment['id']))
        alert_id = cursor.lastrowid
        conn.commit()

        backfill.apply_backfill(conn)

        cursor.execute("""
            SELECT id, monitor_id, monitor_target_id, total_eventos, conclusao
              FROM monitoramento.monitor_analises WHERE id = %s
        """, (analysis_id,))
        assert cursor.fetchone() == {
            'id': analysis_id,
            'monitor_id': assignment['monitor_id'],
            'monitor_target_id': assignment['id'],
            'total_eventos': 1,
            'conclusao': 'Análise temporária UI-3.0E2',
        }
        cursor.execute("""
            SELECT id, analise_id, monitor_id, monitor_target_id, status
              FROM monitoramento.monitor_alertas WHERE id = %s
        """, (alert_id,))
        assert cursor.fetchone() == {
            'id': alert_id,
            'analise_id': analysis_id,
            'monitor_id': assignment['monitor_id'],
            'monitor_target_id': assignment['id'],
            'status': 'pending',
        }
        cursor.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.monitor_alertas '
            'WHERE analise_id IS NULL'
        )
        assert cursor.fetchone()['total'] == 0
    finally:
        if alert_id is not None:
            cursor.execute('DELETE FROM monitoramento.monitor_alertas WHERE id = %s', (alert_id,))
            cursor.execute('DELETE FROM tracker.monitor_alertas WHERE id = %s', (alert_id,))
        if analysis_id is not None:
            cursor.execute('DELETE FROM monitoramento.monitor_analises WHERE id = %s', (analysis_id,))
            cursor.execute('DELETE FROM tracker.monitor_analises WHERE id = %s', (analysis_id,))
        conn.commit()
        cursor.close()
        conn.close()
