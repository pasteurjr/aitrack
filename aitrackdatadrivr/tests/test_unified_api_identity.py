from flask import Flask

from server import unified_api


VEHICLES = [
    {
        'id': 1,
        'device_id': 'SIM-1000',
        'codusu': None,
        'placa': 'AAA0001',
        'tipo': 'tracker_only',
        'descricao': 'Veículo Tracker',
        'ativo': True,
    },
    {
        'id': 2,
        'device_id': None,
        'codusu': 7,
        'placa': 'BBB0002',
        'tipo': 'app_only',
        'descricao': 'Veículo Dirija Bem',
        'ativo': True,
    },
]


def _client(monkeypatch):
    monkeypatch.setattr(
        unified_api.monitor_db,
        'get_all_unified_vehicles',
        lambda: VEHICLES,
    )
    app = Flask(__name__)
    app.register_blueprint(unified_api.unified_bp)
    return app.test_client()


def test_legacy_vehicle_list_contract_uses_identity_repository(monkeypatch):
    monkeypatch.setattr(
        unified_api, 'get_tracker_data',
        lambda device_id: {'device_id': device_id},
    )
    monkeypatch.setattr(
        unified_api, 'get_dirijabem_data',
        lambda codusu: {'ultima_viagem': codusu, 'score': 91},
    )

    response = _client(monkeypatch).get('/api/unified/vehicles')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['total'] == 2
    assert payload['vehicles'][0]['fonte'] == 'tracker'
    assert payload['vehicles'][1]['fonte'] == 'dirijabem'


def test_vehicle_lookup_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        unified_api, 'get_tracker_data_full',
        lambda device_id: {'device_id': device_id},
    )

    response = _client(monkeypatch).get('/api/unified/vehicle/aaa0001')

    assert response.status_code == 200
    assert response.get_json()['vehicle']['tracker']['device_id'] == 'SIM-1000'


def test_stats_are_computed_from_selected_read_model(monkeypatch):
    response = _client(monkeypatch).get('/api/unified/stats')

    assert response.status_code == 200
    assert response.get_json()['stats'] == {
        'por_tipo': [
            {'tipo': 'app_only', 'total': 1},
            {'tipo': 'tracker_only', 'total': 1},
        ],
        'total_geral': 2,
    }


def test_position_returns_not_found_from_selected_read_model(monkeypatch):
    response = _client(monkeypatch).get('/api/unified/position/INEXISTENTE')

    assert response.status_code == 404
    assert response.get_json()['success'] is False
