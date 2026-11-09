"""Prova opt-in do CRUD inicial de cercas no MariaDB compartilhado."""

import os
from uuid import uuid4

import pytest

from server import geofence_db
from server.geofence_geometry import normalize_geometry


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='integração MariaDB desabilitada',
)


def test_creates_lists_and_reads_circle_and_polygon_without_residue():
    marker = f'codex-ui-3-3-{uuid4()}'
    created_ids = []
    base = {
        'descricao': 'Registro temporário do teste UI-3.3',
        'regra': 'allowed',
        'status': 'draft',
        'owner_ref': marker,
        'actor_id': 'codex-integration-test',
        'change_reason': 'Prova automatizada UI-3.3',
    }
    try:
        circle = geofence_db.create_geofence(
            {**base, 'nome': f'{marker}-circle'},
            normalize_geometry({
                'type': 'Circle',
                'center': [-46.6333, -23.5505],
                'radius_meters': 450,
            }),
        )
        created_ids.append(circle['id'])
        polygon = geofence_db.create_geofence(
            {**base, 'nome': f'{marker}-polygon', 'regra': 'forbidden'},
            normalize_geometry({
                'type': 'Polygon',
                'coordinates': [[
                    [-46.64, -23.56], [-46.62, -23.56],
                    [-46.62, -23.54], [-46.64, -23.56],
                ]],
            }),
        )
        created_ids.append(polygon['id'])

        fences, total = geofence_db.list_geofences({'search': marker}, 10, 0)
        detail = geofence_db.get_geofence(circle['public_id'])

        assert total == 2
        assert {fence['geometry_type'] for fence in fences} == {'circle', 'polygon'}
        assert detail['geometry'] == {
            'type': 'Circle',
            'center': [-46.6333, -23.5505],
            'radius_meters': 450.0,
        }
        assert all(fence['active_assignments'] == 0 for fence in fences)
    finally:
        if created_ids:
            conn = geofence_db.get_connection()
            cursor = conn.cursor()
            try:
                placeholders = ','.join(['%s'] * len(created_ids))
                cursor.execute(
                    'DELETE FROM monitoramento.geofence_versions '
                    f'WHERE geofence_id IN ({placeholders})',
                    tuple(created_ids),
                )
                cursor.execute(
                    'DELETE FROM monitoramento.geofences '
                    f'WHERE id IN ({placeholders}) AND owner_ref = %s',
                    tuple(created_ids) + (marker,),
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()
