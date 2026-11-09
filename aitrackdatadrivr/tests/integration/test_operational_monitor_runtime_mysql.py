"""Ciclo real do runtime de monitores no schema operacional."""

import os
from datetime import datetime, timedelta

import pytest

from server.api import app
from server import monitor_db


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)


def _legacy_counts(cursor):
    counts = {}
    for table in ('monitores', 'veiculomonitor', 'monitor_analises', 'monitor_alertas'):
        cursor.execute(f'SELECT COUNT(*) AS total FROM tracker.{table}')
        counts[table] = int(cursor.fetchone()['total'])
    return counts


def test_monitor_target_analysis_and_alert_lifecycle_do_not_write_legacy():
    client = app.test_client()
    conn = monitor_db.get_connection()
    cursor = conn.cursor(dictionary=True)
    monitor_id = target_id = analysis_id = alert_id = None
    try:
        before = _legacy_counts(cursor)
        response = client.post('/api/monitors', json={
            'nome': 'Monitor temporário UI-3.0E3B',
            'descricao': 'Removido automaticamente',
            'tipo_monitor': 'safety',
            'ativo': True,
        })
        assert response.status_code == 201
        monitor_id = response.get_json()['id']

        cursor.execute("""
            SELECT CAST(veicod.valor_externo AS UNSIGNED) AS veicod,
                   device.valor_externo AS device_id
              FROM monitoramento.veiculo_identidades device
              JOIN monitoramento.veiculo_identidades veicod
                ON veicod.vehicle_id = device.vehicle_id
               AND veicod.fonte_codigo = 'tracker'
               AND veicod.tipo_identidade = 'vehicle_id'
             WHERE device.fonte_codigo = 'tracker'
               AND device.tipo_identidade = 'device_id'
             ORDER BY device.id LIMIT 1
        """)
        identity = cursor.fetchone()
        response = client.post(f'/api/monitors/{monitor_id}/vehicles', json=identity)
        assert response.status_code == 201
        target_id = response.get_json()['id']

        response = client.get(f'/api/monitors/{monitor_id}/vehicles')
        assert response.status_code == 200
        assert response.get_json()[0]['id'] == target_id

        now = datetime.now()
        analysis_id = monitor_db.save_analysis(monitor_id, target_id, {
            'periodo_inicio': now - timedelta(minutes=5),
            'periodo_fim': now,
            'total_eventos': 2,
            'score_inicial': 70,
            'score_final': 60,
            'eventos_por_tipo': {'speeding': 2},
            'conclusao': 'Validação operacional',
            'severidade': 'high',
        })
        alert_id = monitor_db.create_alert({
            'analise_id': analysis_id,
            'monitor_id': monitor_id,
            'veiculomonitor_id': target_id,
            'device_id': identity['device_id'],
            'titulo': 'Alerta temporário UI-3.0E3B',
            'mensagem': 'Removido automaticamente',
            'severidade': 'high',
            'tipo': 'safety',
            'total_eventos_relacionados': 2,
        })
        response = client.put(
            f'/api/alerts/{alert_id}/acknowledge',
            json={'reconhecido_por': 'codex-e3b'},
        )
        assert response.status_code == 200
        assert monitor_db.get_alert_by_id(alert_id)['status'] == 'acknowledged'
        assert _legacy_counts(cursor) == before
    finally:
        if alert_id:
            cursor.execute('DELETE FROM monitoramento.monitor_alertas WHERE id = %s', (alert_id,))
        if analysis_id:
            cursor.execute('DELETE FROM monitoramento.monitor_analises WHERE id = %s', (analysis_id,))
        if target_id:
            cursor.execute('DELETE FROM monitoramento.monitor_targets WHERE id = %s', (target_id,))
        if monitor_id:
            cursor.execute('DELETE FROM monitoramento.monitores WHERE id = %s', (monitor_id,))
        conn.commit()
        cursor.close()
        conn.close()
