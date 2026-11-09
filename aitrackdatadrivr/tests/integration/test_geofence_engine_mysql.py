"""Prova opt-in do mesmo motor de cercas nas origens Tracker e Dirija Bem."""

import os
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from server import geofence_assignment_db, geofence_db, geofence_engine
from server.geofence_geometry import normalize_geometry


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='integração MariaDB desabilitada',
)


def _create_fence(marker, rule, target_type, target_id):
    fence = geofence_db.create_geofence({
        'nome': f'{marker}-{target_type}',
        'descricao': 'Cerca temporária UI-3.8',
        'regra': rule,
        'status': 'active',
        'owner_ref': marker,
        'actor_id': 'codex-integration-test',
        'change_reason': 'Prova de transição UI-3.8',
    }, normalize_geometry({
        'type': 'Circle', 'center': [-46.6333, -23.5505],
        'radius_meters': 300,
    }))
    assignment = geofence_assignment_db.assign_target(fence['public_id'], {
        'target_type': target_type,
        'target_id': target_id,
        'actor_id': 'codex-integration-test',
    })
    return fence, assignment


def test_confirms_tracker_exit_and_dirijabem_entry_without_duplicates():
    marker = f'codex-ui-3-8-{uuid4()}'
    conn = geofence_db.get_connection()
    cursor = conn.cursor(dictionary=True)
    fences = []
    link_id = None
    try:
        cursor.execute("""
            SELECT device.vehicle_id, device.valor_externo AS device_id,
                   veicod.valor_externo AS veicod
              FROM monitoramento.veiculo_identidades device
              JOIN monitoramento.veiculo_identidades veicod
                ON veicod.vehicle_id = device.vehicle_id
               AND veicod.fonte_codigo = 'tracker'
               AND veicod.tipo_identidade = 'vehicle_id' AND veicod.ativo = TRUE
             WHERE device.fonte_codigo = 'tracker'
               AND device.tipo_identidade = 'device_id' AND device.ativo = TRUE
             ORDER BY device.id LIMIT 1
        """)
        tracker = cursor.fetchone()
        cursor.execute("""
            SELECT mi.driver_id, mi.valor_externo AS codusu
              FROM monitoramento.motorista_identidades mi
             WHERE mi.fonte_codigo = 'dirijabem'
               AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
             ORDER BY mi.id LIMIT 1
        """)
        dirijabem = cursor.fetchone()
        if not tracker or not dirijabem:
            pytest.skip('identidades canônicas das duas fontes indisponíveis')

        cursor.execute("""
            INSERT INTO monitoramento.veiculo_motorista_vinculos
                (vehicle_id, driver_id, fonte_codigo, valido_desde)
            VALUES (%s, %s, 'dirijabem', %s)
        """, (tracker['vehicle_id'], dirijabem['driver_id'], datetime.now()))
        link_id = cursor.lastrowid
        conn.commit()

        tracker_fence, tracker_assignment = _create_fence(
            marker, 'allowed', 'vehicle', tracker['vehicle_id'],
        )
        fences.append(tracker_fence['id'])
        driver_fence, driver_assignment = _create_fence(
            marker, 'forbidden', 'driver', dirijabem['driver_id'],
        )
        fences.append(driver_fence['id'])

        now = datetime.now()
        tracker_assignment = geofence_assignment_db.update_assignment_policy(
            tracker_fence['public_id'], tracker_assignment['id'], {
                'expected_version': 1,
                'timezone_name': 'America/Sao_Paulo',
                'dwell_threshold_seconds': 2,
                'schedules': [{
                    'day_of_week': now.weekday(), 'start_time': '00:00:00',
                    'end_time': '23:59:59', 'crosses_midnight': False,
                }],
                'actor_id': 'codex-integration-test',
            },
        )
        tracker_clock = now + timedelta(hours=3)
        inside = (-46.6333, -23.5505)
        outside = (-46.6200, -23.5505)

        assert geofence_engine.evaluate_tracker_position(
            tracker['device_id'], tracker['veicod'], *inside, tracker_clock,
            received_at=now, external_position_id=f'{marker}:tracker:1',
        ) == []
        assert geofence_engine.evaluate_dirijabem_position(
            dirijabem['codusu'], *outside, now,
            received_at=now + timedelta(seconds=1),
            external_position_id=f'{marker}:dirijabem:1',
        ) == []
        tracker_events = geofence_engine.evaluate_dirijabem_position(
            dirijabem['codusu'], *outside, now + timedelta(seconds=1),
            received_at=now + timedelta(seconds=2),
            external_position_id=f'{marker}:dirijabem:2',
        )
        assert [event['event_type'] for event in tracker_events] == ['geofence_exit']
        assert tracker_events[0]['assignment_id'] == tracker_assignment['id']

        dwell_events = geofence_engine.evaluate_dirijabem_position(
            dirijabem['codusu'], *outside, now + timedelta(seconds=3),
            received_at=now + timedelta(seconds=4),
            external_position_id=f'{marker}:dirijabem:3',
        )
        assert [event['event_type'] for event in dwell_events] == ['geofence_dwell']

        assert geofence_engine.evaluate_tracker_position(
            tracker['device_id'], tracker['veicod'], *inside,
            tracker_clock + timedelta(seconds=1),
            received_at=now + timedelta(seconds=5),
            external_position_id=f'{marker}:tracker:2',
        ) == []
        driver_events = geofence_engine.evaluate_tracker_position(
            tracker['device_id'], tracker['veicod'], *inside,
            tracker_clock + timedelta(seconds=2),
            received_at=now + timedelta(seconds=6),
            external_position_id=f'{marker}:tracker:3',
        )
        assert [event['event_type'] for event in driver_events] == ['geofence_entry']
        assert driver_events[0]['assignment_id'] == driver_assignment['id']

        # Repetição do pacote e novas posições estáveis não criam outro evento.
        assert geofence_engine.evaluate_tracker_position(
            tracker['device_id'], tracker['veicod'], *inside,
            tracker_clock + timedelta(seconds=2),
            received_at=now + timedelta(seconds=6),
            external_position_id=f'{marker}:tracker:3',
        ) == []
        assert geofence_engine.evaluate_tracker_position(
            tracker['device_id'], tracker['veicod'], *inside,
            tracker_clock + timedelta(seconds=3),
            received_at=now + timedelta(seconds=7),
            external_position_id=f'{marker}:tracker:4',
        ) == []

        conn.commit()  # encerra o snapshot aberto durante a busca das identidades
        cursor.execute("""
            SELECT source_code, event_type, crossing_direction
              FROM monitoramento.geofence_events
             WHERE geofence_id IN (%s, %s) ORDER BY observed_at, id
        """, tuple(fences))
        assert cursor.fetchall() == [
            {
                'source_code': 'dirijabem', 'event_type': 'geofence_exit',
                'crossing_direction': 'inside_to_outside',
            },
            {
                'source_code': 'dirijabem', 'event_type': 'geofence_dwell',
                'crossing_direction': None,
            },
            {
                'source_code': 'tracker', 'event_type': 'geofence_entry',
                'crossing_direction': 'outside_to_inside',
            },
        ]
    finally:
        if fences:
            placeholders = ','.join(['%s'] * len(fences))
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_events WHERE geofence_id IN ({placeholders})',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_target_states WHERE assignment_id IN '
                f'(SELECT id FROM monitoramento.geofence_assignments '
                f'WHERE geofence_id IN ({placeholders}))',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_assignment_schedules WHERE assignment_id IN '
                f'(SELECT id FROM monitoramento.geofence_assignments '
                f'WHERE geofence_id IN ({placeholders}))',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_assignments WHERE geofence_id IN ({placeholders})',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_audit_log WHERE geofence_id IN ({placeholders})',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofence_versions WHERE geofence_id IN ({placeholders})',
                tuple(fences),
            )
            cursor.execute(
                f'DELETE FROM monitoramento.geofences WHERE id IN ({placeholders}) AND owner_ref = %s',
                tuple(fences) + (marker,),
            )
            cursor.execute(
                'DELETE FROM monitoramento.source_position_receipts '
                'WHERE external_position_id LIKE %s',
                (f'{marker}:%',),
            )
            if link_id:
                cursor.execute(
                    'DELETE FROM monitoramento.veiculo_motorista_vinculos WHERE id = %s',
                    (link_id,),
                )
            conn.commit()
        cursor.close()
        conn.close()
