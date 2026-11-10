"""Replay determinístico completo contra o schema operacional real."""

import os
from datetime import timedelta
from uuid import uuid4

import pytest

from server import geofence_assignment_db, geofence_db, geofence_engine, geofence_live_db
from server.geofence_geometry import normalize_geometry
from server.geofence_replay import execute_replay, standard_scenarios, validate_replay


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)


def _delete_fence(cursor, fence_id):
    cursor.execute(
        'SELECT DISTINCT incident_id FROM monitoramento.geofence_events '
        'WHERE geofence_id = %s AND incident_id IS NOT NULL',
        (fence_id,),
    )
    incident_ids = [row['incident_id'] for row in cursor.fetchall()]
    cursor.execute(
        'DELETE FROM monitoramento.geofence_events WHERE geofence_id = %s',
        (fence_id,),
    )
    if incident_ids:
        placeholders = ','.join(['%s'] * len(incident_ids))
        cursor.execute(
            f'DELETE FROM monitoramento.incident_timeline '
            f'WHERE incident_id IN ({placeholders})',
            tuple(incident_ids),
        )
        cursor.execute(
            f'DELETE FROM monitoramento.incidents '
            f'WHERE id IN ({placeholders})',
            tuple(incident_ids),
        )
    cursor.execute(
        'DELETE FROM monitoramento.geofence_target_states '
        'WHERE assignment_id IN '
        '(SELECT id FROM monitoramento.geofence_assignments WHERE geofence_id = %s)',
        (fence_id,),
    )
    cursor.execute(
        'DELETE FROM monitoramento.geofence_assignment_schedules '
        'WHERE assignment_id IN '
        '(SELECT id FROM monitoramento.geofence_assignments WHERE geofence_id = %s)',
        (fence_id,),
    )
    cursor.execute(
        'DELETE FROM monitoramento.geofence_assignments WHERE geofence_id = %s',
        (fence_id,),
    )
    cursor.execute(
        'DELETE FROM monitoramento.geofence_audit_log WHERE geofence_id = %s',
        (fence_id,),
    )
    cursor.execute(
        'DELETE FROM monitoramento.geofence_versions WHERE geofence_id = %s',
        (fence_id,),
    )
    cursor.execute(
        'DELETE FROM monitoramento.geofences WHERE id = %s',
        (fence_id,),
    )


def test_standard_replay_produces_exact_episodes_without_residue():
    marker = f'codex-ui-3-11-{uuid4()}'
    device_id = f'{marker}-device'
    external_vehicle_id = f'{marker}-vehicle'
    conn = geofence_db.get_connection()
    cursor = conn.cursor(dictionary=True)
    vehicle_id = None
    fence_ids = []
    all_fence_ids = []
    all_assignment_ids = []
    all_incident_ids = []
    try:
        assert geofence_engine.CONFIRMATION_SAMPLES == 2
        cursor.execute("""
            INSERT INTO monitoramento.veiculos
                (public_id, placa, descricao, ativo)
            VALUES (%s, %s, %s, TRUE)
        """, (str(uuid4()), marker[-20:], 'Veículo temporário do replay UI-3.11'))
        vehicle_id = cursor.lastrowid
        cursor.executemany("""
            INSERT INTO monitoramento.veiculo_identidades
                (vehicle_id, fonte_codigo, tipo_identidade, valor_externo,
                 principal, ativo)
            VALUES (%s, 'tracker', %s, %s, %s, TRUE)
        """, (
            (vehicle_id, 'device_id', device_id, True),
            (vehicle_id, 'vehicle_id', external_vehicle_id, False),
        ))
        conn.commit()

        for scenario in standard_scenarios():
            fence = geofence_db.create_geofence({
                'nome': f'{marker}-{scenario.name}',
                'descricao': 'Replay determinístico temporário UI-3.11',
                'regra': scenario.rule,
                'status': 'active',
                'owner_ref': marker,
                'actor_id': 'codex-replay-test',
                'change_reason': f'Cenário {scenario.name}',
            }, normalize_geometry(scenario.geometry))
            fence_ids.append(fence['id'])
            all_fence_ids.append(fence['id'])
            assignment = geofence_assignment_db.assign_target(fence['public_id'], {
                'target_type': 'vehicle',
                'target_id': vehicle_id,
                'notify_on_entry': True,
                'notify_on_exit': True,
                'actor_id': 'codex-replay-test',
            })
            all_assignment_ids.append(assignment['id'])
            geofence_assignment_db.update_assignment_policy(
                fence['public_id'], assignment['id'], {
                    'expected_version': assignment['version'],
                    'timezone_name': 'America/Sao_Paulo',
                    'dwell_threshold_seconds': scenario.dwell_threshold_seconds,
                    'schedules': list(scenario.schedules),
                    'actor_id': 'codex-replay-test',
                },
            )
            geofence_engine.clear_assignment_cache()

            events = execute_replay(
                scenario,
                lambda **point: geofence_engine.evaluate_tracker_position(
                    device_id=device_id,
                    vehicle_id=external_vehicle_id,
                    **point,
                ),
                marker,
            )
            validate_replay(scenario, events)
            assert execute_replay(
                scenario,
                lambda **point: geofence_engine.evaluate_tracker_position(
                    device_id=device_id,
                    vehicle_id=external_vehicle_id,
                    **point,
                ),
                marker,
            ) == []

            conn.commit()
            cursor.execute("""
                SELECT event_type, crossing_direction, violation_episode_id,
                       incident_id, correlation_status, observed_at
                  FROM monitoramento.geofence_events
                 WHERE geofence_id = %s ORDER BY received_at, id
            """, (fence['id'],))
            stored = cursor.fetchall()
            assert [item['event_type'] for item in stored] == [
                item.event_type for item in scenario.expected_events
            ]
            assert [item['crossing_direction'] for item in stored] == [
                item.crossing_direction for item in scenario.expected_events
            ]
            assert len({item['violation_episode_id'] for item in stored}) == 1
            assert len({item['incident_id'] for item in stored}) == 1
            assert all(item['correlation_status'] == 'correlated' for item in stored)

            incident_id = stored[0]['incident_id']
            all_incident_ids.append(incident_id)
            cursor.execute(
                'SELECT event_count, severity FROM monitoramento.incidents WHERE id = %s',
                (incident_id,),
            )
            assert cursor.fetchone() == {
                'event_count': len(scenario.expected_events),
                'severity': 'critical',
            }
            cursor.execute(
                'SELECT COUNT(*) AS total FROM monitoramento.incident_timeline '
                'WHERE incident_id = %s AND evidence_type = %s',
                (incident_id, 'geofence_event'),
            )
            assert cursor.fetchone()['total'] == len(scenario.expected_events)

            snapshot = geofence_live_db.get_live_state(
                now=scenario.start_at + timedelta(
                    seconds=scenario.points[-1].offset_seconds,
                ),
            )
            live_fence = next(item for item in snapshot if item['id'] == fence['id'])
            assert live_fence['geometry']['type'] == scenario.geometry['type']
            assert live_fence['regra'] == scenario.rule
            assert live_fence['live_summary']['targets'] == 1
            live_target = live_fence['targets'][0]
            assert live_target['target_label']
            assert live_target['stable_state'] == (
                'inside' if scenario.rule == 'allowed' else 'outside'
            )
            assert live_target['schedule_active'] is True
            assert live_target['active_episode'] is False
            assert live_target['last_source'] == 'tracker'
            assert live_target['last_evaluated_at']
            assert live_target['last_position'] is not None

            _delete_fence(cursor, fence['id'])
            cursor.execute(
                'DELETE FROM monitoramento.source_position_receipts '
                'WHERE external_position_id LIKE %s',
                (f'{marker}:{scenario.name}:%',),
            )
            conn.commit()
            fence_ids.remove(fence['id'])
            geofence_engine.clear_assignment_cache()
    finally:
        for fence_id in list(fence_ids):
            _delete_fence(cursor, fence_id)
        cursor.execute(
            'DELETE FROM monitoramento.source_position_receipts '
            'WHERE external_position_id LIKE %s',
            (f'{marker}:%',),
        )
        if vehicle_id is not None:
            cursor.execute(
                'DELETE FROM monitoramento.veiculo_identidades WHERE vehicle_id = %s',
                (vehicle_id,),
            )
            cursor.execute(
                'DELETE FROM monitoramento.veiculos WHERE id = %s',
                (vehicle_id,),
            )
        conn.commit()
        geofence_engine.clear_assignment_cache()
        cursor.close()
        conn.close()

    verification = geofence_db.get_connection()
    check = verification.cursor(dictionary=True)
    try:
        fence_placeholders = ','.join(['%s'] * len(all_fence_ids))
        assignment_placeholders = ','.join(['%s'] * len(all_assignment_ids))
        incident_placeholders = ','.join(['%s'] * len(all_incident_ids))
        for table, column, placeholders, values in (
            ('geofence_events', 'geofence_id', fence_placeholders, all_fence_ids),
            ('geofence_target_states', 'assignment_id', assignment_placeholders,
             all_assignment_ids),
            ('geofence_assignment_schedules', 'assignment_id', assignment_placeholders,
             all_assignment_ids),
            ('geofence_assignments', 'id', assignment_placeholders, all_assignment_ids),
            ('geofence_audit_log', 'geofence_id', fence_placeholders, all_fence_ids),
            ('geofence_versions', 'geofence_id', fence_placeholders, all_fence_ids),
            ('geofences', 'id', fence_placeholders, all_fence_ids),
            ('incident_timeline', 'incident_id', incident_placeholders, all_incident_ids),
            ('incidents', 'id', incident_placeholders, all_incident_ids),
        ):
            check.execute(
                f'SELECT COUNT(*) AS total FROM monitoramento.{table} '
                f'WHERE {column} IN ({placeholders})',
                tuple(values),
            )
            assert check.fetchone()['total'] == 0, f'resíduo em {table}'
        check.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.geofences WHERE owner_ref = %s',
            (marker,),
        )
        assert check.fetchone()['total'] == 0
        check.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.veiculos WHERE id = %s',
            (vehicle_id,),
        )
        assert check.fetchone()['total'] == 0
        check.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.veiculo_identidades '
            'WHERE valor_externo IN (%s, %s)',
            (device_id, external_vehicle_id),
        )
        assert check.fetchone()['total'] == 0
        check.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.source_position_receipts '
            'WHERE external_position_id LIKE %s',
            (f'{marker}:%',),
        )
        assert check.fetchone()['total'] == 0
    finally:
        check.close()
        verification.close()
