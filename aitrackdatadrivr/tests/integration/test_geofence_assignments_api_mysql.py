"""Prova opt-in de grupos e atribuições canônicas de cerca."""

import os
from uuid import uuid4

import pytest

from server import geofence_assignment_db, geofence_db
from server.geofence_geometry import normalize_geometry


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='integração MariaDB desabilitada',
)


def test_assigns_vehicle_driver_and_group_with_safe_reactivation():
    marker = f'codex-ui-3-7-{uuid4()}'
    geofence_id = group_id = None
    assignment_ids = []
    try:
        options = geofence_assignment_db.assignment_options()
        vehicle_id = options['vehicles'][0]['id']
        driver_id = options['drivers'][0]['id']
        group = geofence_assignment_db.create_group({
            'nome': marker,
            'descricao': 'Grupo temporário UI-3.7',
            'owner_ref': marker,
            'vehicle_ids': [vehicle_id],
            'driver_ids': [driver_id],
            'actor_id': 'codex-integration-test',
        })
        group_id = group['id']
        assert group['member_count'] == 2

        fence = geofence_db.create_geofence({
            'nome': marker, 'descricao': 'Cerca temporária UI-3.7',
            'regra': 'allowed', 'status': 'active', 'owner_ref': marker,
            'actor_id': 'codex-integration-test', 'change_reason': 'Prova UI-3.7',
        }, normalize_geometry({
            'type': 'Circle', 'center': [-46.6333, -23.5505], 'radius_meters': 300,
        }))
        geofence_id = fence['id']

        created = []
        for target_type, target_id in (
            ('vehicle', vehicle_id), ('driver', driver_id), ('group', group_id),
        ):
            assignment = geofence_assignment_db.assign_target(fence['public_id'], {
                'target_type': target_type, 'target_id': target_id,
                'actor_id': 'codex-integration-test',
            })
            created.append(assignment)
            assignment_ids.append(assignment['id'])
        assert {item['target_type'] for item in created} == {'vehicle', 'driver', 'group'}
        assert all(item['notify_on_exit'] and not item['notify_on_entry'] for item in created)

        with pytest.raises(geofence_assignment_db.AssignmentConflict):
            geofence_assignment_db.assign_target(fence['public_id'], {
                'target_type': 'vehicle', 'target_id': vehicle_id,
                'actor_id': 'codex-integration-test',
            })

        deactivated = geofence_assignment_db.deactivate_assignment(
            fence['public_id'], created[0]['id'], {
                'expected_version': 1, 'actor_id': 'codex-integration-test',
            },
        )
        assert deactivated['ativo'] is False and deactivated['version'] == 2
        reactivated = geofence_assignment_db.assign_target(fence['public_id'], {
            'target_type': 'vehicle', 'target_id': vehicle_id,
            'actor_id': 'codex-integration-test',
        })
        assert reactivated['ativo'] is True and reactivated['version'] == 3
        assert len(geofence_assignment_db.list_assignments(fence['public_id'])) == 3
    finally:
        conn = geofence_db.get_connection()
        cursor = conn.cursor()
        try:
            if geofence_id:
                cursor.execute(
                    'DELETE FROM monitoramento.geofence_assignments WHERE geofence_id = %s',
                    (geofence_id,),
                )
                cursor.execute(
                    'DELETE FROM monitoramento.geofence_audit_log WHERE geofence_id = %s',
                    (geofence_id,),
                )
                cursor.execute(
                    'DELETE FROM monitoramento.geofence_versions WHERE geofence_id = %s',
                    (geofence_id,),
                )
                cursor.execute(
                    'DELETE FROM monitoramento.geofences WHERE id = %s AND owner_ref = %s',
                    (geofence_id, marker),
                )
            if group_id:
                cursor.execute(
                    'DELETE FROM monitoramento.monitoring_group_members WHERE group_id = %s',
                    (group_id,),
                )
                cursor.execute(
                    'DELETE FROM monitoramento.monitoring_groups WHERE id = %s AND owner_ref = %s',
                    (group_id, marker),
                )
            conn.commit()
        finally:
            cursor.close()
            conn.close()
