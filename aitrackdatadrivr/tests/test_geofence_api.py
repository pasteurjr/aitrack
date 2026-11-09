import pytest
from flask import Flask

from server import geofence_api
from server.geofence_geometry import normalize_geometry


def _client():
    app = Flask(__name__)
    app.register_blueprint(geofence_api.geofence_bp)
    return app.test_client()


def _circle_payload(**overrides):
    return {
        'nome': 'Base operacional',
        'descricao': 'Área permitida da frota',
        'regra': 'allowed',
        'status': 'active',
        'operator': {'id': 'operator-7', 'name': 'Maria'},
        'geometry': {
            'type': 'Circle',
            'center': [-46.6333, -23.5505],
            'radius_meters': 500,
        },
        **overrides,
    }


def test_normalizes_circle_to_point_wkt_and_stable_hash():
    geometry = normalize_geometry(_circle_payload()['geometry'])

    assert geometry['type'] == 'circle'
    assert geometry['wkt'] == 'POINT(-46.6333 -23.5505)'
    assert geometry['radius_meters'] == 500
    assert len(geometry['hash']) == 64
    assert geometry['hash'] == normalize_geometry(_circle_payload()['geometry'])['hash']


def test_normalizes_closed_geojson_polygon():
    geometry = normalize_geometry({
        'type': 'Polygon',
        'coordinates': [[
            [-46.64, -23.56], [-46.62, -23.56],
            [-46.62, -23.54], [-46.64, -23.56],
        ]],
    })

    assert geometry['type'] == 'polygon'
    assert geometry['wkt'].startswith('POLYGON((')
    assert geometry['radius_meters'] is None


@pytest.mark.parametrize(('geometry', 'message'), [
    ({'type': 'Circle', 'center': [-181, 0], 'radius_meters': 10}, 'longitude'),
    ({'type': 'Circle', 'center': [0, 91], 'radius_meters': 10}, 'latitude'),
    ({'type': 'Circle', 'center': [0, 0], 'radius_meters': 0}, 'radius_meters'),
    ({'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [0, 1]]]}, 'fechado'),
    ({
        'type': 'Polygon',
        'coordinates': [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]],
    }, 'auto-interseções'),
])
def test_rejects_invalid_geometry(geometry, message):
    with pytest.raises(ValueError, match=message):
        normalize_geometry(geometry)


def test_lists_geofences_with_whitelisted_filters(monkeypatch):
    captured = {}

    def fake_list(filters, limit, offset):
        captured.update(filters=filters, limit=limit, offset=offset)
        return ([{'id': 4, 'nome': 'Garagem'}], 1)

    monkeypatch.setattr(geofence_api.geofence_db, 'list_geofences', fake_list)
    response = _client().get(
        '/api/geofences?status=active&regra=allowed&search=garage&limit=20&offset=2',
    )

    assert response.status_code == 200
    assert response.get_json()['schema_version'] == 'geofence-list.v1'
    assert response.get_json()['total'] == 1
    assert captured == {
        'filters': {'status': 'active', 'regra': 'allowed', 'search': 'garage'},
        'limit': 20,
        'offset': 2,
    }


def test_rejects_invalid_filter_before_database(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_db,
        'list_geofences',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )

    response = _client().get('/api/geofences?status=apagada')

    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_GEOFENCE_FILTER'


def test_creates_audited_geofence_and_geometry(monkeypatch):
    captured = {}

    def fake_create(data, geometry):
        captured.update(data=data, geometry=geometry)
        return {'id': 8, 'nome': data['nome'], 'geometry': geometry['geometry']}

    monkeypatch.setattr(geofence_api.geofence_db, 'create_geofence', fake_create)
    response = _client().post('/api/geofences', json=_circle_payload())

    assert response.status_code == 201
    assert response.get_json()['geofence']['id'] == 8
    assert captured['data']['actor_id'] == 'operator-7'
    assert captured['data']['change_reason'] == 'Criação inicial'
    assert captured['geometry']['type'] == 'circle'


def test_returns_detail_by_reference_or_not_found(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_db,
        'get_geofence',
        lambda reference: {'id': 9, 'public_id': reference} if reference == 'public-9' else None,
    )

    found = _client().get('/api/geofences/public-9')
    missing = _client().get('/api/geofences/missing')

    assert found.status_code == 200
    assert found.get_json()['schema_version'] == 'geofence-detail.v1'
    assert missing.status_code == 404
    assert missing.get_json()['code'] == 'GEOFENCE_NOT_FOUND'


def test_database_error_does_not_leak_details(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_db,
        'create_geofence',
        lambda *_args: (_ for _ in ()).throw(RuntimeError('senha secreta')),
    )

    response = _client().post('/api/geofences', json=_circle_payload())

    assert response.status_code == 500
    assert response.get_json()['code'] == 'GEOFENCE_CREATE_FAILED'
    assert b'senha secreta' not in response.data


def test_updates_with_expected_version_and_optional_geometry(monkeypatch):
    captured = {}

    def fake_update(reference, data, geometry):
        captured.update(reference=reference, data=data, geometry=geometry)
        return {'id': 8, 'version': 3, 'geometry_version': 2}

    monkeypatch.setattr(geofence_api.geofence_db, 'update_geofence', fake_update)
    response = _client().put('/api/geofences/public-8', json={
        **_circle_payload(),
        'expected_version': 2,
        'change_reason': 'Ajuste solicitado pelo operador',
    })

    assert response.status_code == 200
    assert captured['reference'] == 'public-8'
    assert captured['data']['expected_version'] == 2
    assert captured['geometry']['type'] == 'circle'
    assert response.get_json()['geofence']['geometry_version'] == 2


def test_archives_with_reason_without_physical_delete(monkeypatch):
    captured = {}

    def fake_archive(reference, data):
        captured.update(reference=reference, data=data)
        return {'id': 8, 'status': 'archived', 'version': 4}

    monkeypatch.setattr(geofence_api.geofence_db, 'archive_geofence', fake_archive)
    response = _client().delete('/api/geofences/8', json={
        'expected_version': 3,
        'operator': {'id': 'operator-7', 'name': 'Maria'},
        'change_reason': 'Cerca substituída por outra área',
    })

    assert response.status_code == 200
    assert captured['data']['expected_version'] == 3
    assert response.get_json()['geofence']['status'] == 'archived'


@pytest.mark.parametrize(('exception', 'code'), [
    (geofence_api.geofence_db.GeofenceNotFound(), 'GEOFENCE_NOT_FOUND'),
    (geofence_api.geofence_db.GeofenceConflict(), 'GEOFENCE_VERSION_CONFLICT'),
    (geofence_api.geofence_db.GeofenceArchived(), 'GEOFENCE_ARCHIVED'),
    (geofence_api.geofence_db.GeofenceHasActiveAssignments(2), 'GEOFENCE_HAS_ACTIVE_ASSIGNMENTS'),
])
def test_mutation_errors_have_stable_codes(monkeypatch, exception, code):
    monkeypatch.setattr(
        geofence_api.geofence_db,
        'archive_geofence',
        lambda *_args: (_ for _ in ()).throw(exception),
    )
    response = _client().delete('/api/geofences/8', json={
        'expected_version': 3,
        'operator': {'id': 'operator-7', 'name': 'Maria'},
        'change_reason': 'Motivo operacional válido',
    })

    assert response.status_code in {404, 409}
    assert response.get_json()['code'] == code


def test_rejects_update_without_concurrency_version(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_db,
        'update_geofence',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )
    response = _client().put('/api/geofences/8', json=_circle_payload())

    assert response.status_code == 400
    assert response.get_json()['error'] == 'expected_version deve ser inteiro positivo'


def test_lists_assignment_options_from_canonical_identity(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'assignment_options',
        lambda: {'vehicles': [{'id': 1}], 'drivers': [{'id': 2}], 'groups': [{'id': 3}]},
    )
    response = _client().get('/api/geofences/assignment-options')

    assert response.status_code == 200
    assert response.get_json()['schema_version'] == 'geofence-assignment-options.v1'
    assert response.get_json()['vehicles'] == [{'id': 1}]


def test_assigns_canonical_target_with_audited_operator(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'assign_target',
        lambda reference, data: captured.update(reference=reference, data=data) or {'id': 10},
    )
    response = _client().post('/api/geofences/fence-1/assignments', json={
        'target_type': 'driver', 'target_id': 4,
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 201
    assert captured == {
        'reference': 'fence-1',
        'data': {'target_type': 'driver', 'target_id': 4, 'actor_id': 'operator-7'},
    }


def test_deactivates_assignment_with_optimistic_version(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'deactivate_assignment',
        lambda reference, assignment_id, data: captured.update(
            reference=reference, assignment_id=assignment_id, data=data,
        ) or {'id': assignment_id, 'ativo': False},
    )
    response = _client().delete('/api/geofences/fence-1/assignments/10', json={
        'expected_version': 2,
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 200
    assert captured['data'] == {'expected_version': 2, 'actor_id': 'operator-7'}


def test_updates_assignment_schedule_and_dwell_policy(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'update_assignment_policy',
        lambda reference, assignment_id, data: captured.update(
            reference=reference, assignment_id=assignment_id, data=data,
        ) or {'id': assignment_id, 'version': 3},
    )
    response = _client().put('/api/geofences/fence-1/assignments/10', json={
        'expected_version': 2,
        'timezone_name': 'America/Sao_Paulo',
        'dwell_threshold_seconds': 900,
        'schedules': [{
            'day_of_week': 0, 'start_time': '22:00', 'end_time': '06:00',
            'crosses_midnight': True,
        }],
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 200
    assert captured['data']['dwell_threshold_seconds'] == 900
    assert captured['data']['schedules'][0] == {
        'day_of_week': 0, 'start_time': '22:00:00',
        'end_time': '06:00:00', 'crosses_midnight': True,
    }


def test_rejects_incompatible_schedule_before_database(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'update_assignment_policy',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )
    response = _client().put('/api/geofences/fence-1/assignments/10', json={
        'expected_version': 2,
        'timezone_name': 'America/Sao_Paulo',
        'dwell_threshold_seconds': None,
        'schedules': [{
            'day_of_week': 0, 'start_time': '22:00', 'end_time': '06:00',
            'crosses_midnight': False,
        }],
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 400
    assert 'incompatíveis' in response.get_json()['error']


def test_rejects_overlapping_weekly_schedules(monkeypatch):
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'update_assignment_policy',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )
    response = _client().put('/api/geofences/fence-1/assignments/10', json={
        'expected_version': 2, 'timezone_name': 'America/Sao_Paulo',
        'dwell_threshold_seconds': 60,
        'schedules': [
            {'day_of_week': 0, 'start_time': '08:00', 'end_time': '12:00'},
            {'day_of_week': 0, 'start_time': '11:00', 'end_time': '13:00'},
        ],
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 400
    assert 'sobrepor' in response.get_json()['error']


def test_creates_group_with_deduplicated_members(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        geofence_api.geofence_assignment_db,
        'create_group',
        lambda data: captured.update(data) or {'id': 5, 'member_count': 3},
    )
    response = _client().post('/api/geofences/monitoring-groups', json={
        'nome': 'Equipe Norte', 'vehicle_ids': [2, 1, 2], 'driver_ids': [4],
        'operator': {'id': 'operator-7', 'name': 'Maria'},
    })

    assert response.status_code == 201
    assert captured['vehicle_ids'] == [1, 2]
    assert captured['driver_ids'] == [4]


def test_repository_filters_are_parameterized():
    from server import geofence_db

    where, params = geofence_db._where_clause({
        'status': 'active',
        'regra': 'allowed',
        'search': "x' OR 1=1 --",
        'malicious': 'ignored',
    })

    assert where == ' WHERE g.status = %s AND g.regra = %s AND (g.nome LIKE %s OR g.descricao LIKE %s)'
    assert params == ['active', 'allowed', "%x' OR 1=1 --%", "%x' OR 1=1 --%"]
