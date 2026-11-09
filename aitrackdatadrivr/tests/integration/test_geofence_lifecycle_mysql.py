"""Prova opt-in de versão, concorrência e arquivamento seguro de cercas."""

import os
from uuid import uuid4

import pytest

from server import geofence_db
from server.geofence_geometry import normalize_geometry


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='integração MariaDB desabilitada',
)


def test_versions_geometry_rejects_stale_write_and_blocks_assigned_archive():
    marker = f'codex-ui-3-6-{uuid4()}'
    geofence_id = None
    assignment_id = None
    base = {
        'nome': marker,
        'descricao': 'Cerca temporária UI-3.6',
        'regra': 'allowed',
        'status': 'draft',
        'owner_ref': marker,
        'actor_id': 'codex-integration-test',
        'change_reason': 'Criação da prova UI-3.6',
    }
    try:
        created = geofence_db.create_geofence(
            base,
            normalize_geometry({
                'type': 'Circle', 'center': [-46.6333, -23.5505],
                'radius_meters': 300,
            }),
        )
        geofence_id = created['id']
        updated = geofence_db.update_geofence(
            created['public_id'],
            {
                **base,
                'nome': f'{marker}-updated',
                'regra': 'forbidden',
                'status': 'active',
                'expected_version': 1,
                'change_reason': 'Redesenho para polígono',
            },
            normalize_geometry({
                'type': 'Polygon',
                'coordinates': [[
                    [-46.64, -23.56], [-46.62, -23.56],
                    [-46.62, -23.54], [-46.64, -23.56],
                ]],
            }),
        )
        assert updated['version'] == 2
        assert updated['geometry_version'] == 2
        assert updated['geometry_type'] == 'polygon'

        with pytest.raises(geofence_db.GeofenceConflict):
            geofence_db.update_geofence(
                str(geofence_id), {**base, 'expected_version': 1}, None,
            )

        conn = geofence_db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT id FROM monitoramento.veiculos ORDER BY id LIMIT 1')
            vehicle_id = cursor.fetchone()['id']
            cursor.execute(
                """
                INSERT INTO monitoramento.geofence_assignments
                    (geofence_id, target_type, vehicle_id, criado_por, atualizado_por)
                VALUES (%s, 'vehicle', %s, %s, %s)
                """,
                (geofence_id, vehicle_id, marker, marker),
            )
            assignment_id = cursor.lastrowid
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        archive_data = {
            'expected_version': 2,
            'actor_id': 'codex-integration-test',
            'change_reason': 'Fim da prova UI-3.6',
        }
        with pytest.raises(geofence_db.GeofenceHasActiveAssignments) as blocked:
            geofence_db.archive_geofence(str(geofence_id), archive_data)
        assert blocked.value.count == 1

        conn = geofence_db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE monitoramento.geofence_assignments SET ativo = FALSE '
                'WHERE id = %s AND geofence_id = %s',
                (assignment_id, geofence_id),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        archived = geofence_db.archive_geofence(str(geofence_id), archive_data)
        assert archived['status'] == 'archived'
        assert archived['version'] == 3

        conn = geofence_db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                'SELECT action, from_version, to_version '
                'FROM monitoramento.geofence_audit_log '
                'WHERE geofence_id = %s ORDER BY id',
                (geofence_id,),
            )
            assert cursor.fetchall() == [
                {'action': 'created', 'from_version': None, 'to_version': 1},
                {'action': 'geometry_updated', 'from_version': 1, 'to_version': 2},
                {'action': 'archived', 'from_version': 2, 'to_version': 3},
            ]
        finally:
            cursor.close()
            conn.close()
    finally:
        if geofence_id:
            conn = geofence_db.get_connection()
            cursor = conn.cursor()
            try:
                if assignment_id:
                    cursor.execute(
                        'DELETE FROM monitoramento.geofence_assignments '
                        'WHERE id = %s AND geofence_id = %s',
                        (assignment_id, geofence_id),
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
                conn.commit()
            finally:
                cursor.close()
                conn.close()
