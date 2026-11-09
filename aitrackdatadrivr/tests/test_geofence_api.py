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
