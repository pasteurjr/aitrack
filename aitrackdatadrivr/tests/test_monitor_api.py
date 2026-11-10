from flask import Flask

from server import monitor_api


def _client():
    app = Flask(__name__)
    app.register_blueprint(monitor_api.monitor_bp)
    return app.test_client()


def test_monitor_vehicles_uses_real_behavioral_values(monkeypatch):
    monkeypatch.setattr(
        monitor_api.monitor_db,
        'get_monitor_vehicles',
        lambda _monitor_id: [{'device_id': 'SIM-1000'}],
    )
    monkeypatch.setattr(monitor_api, 'get_vehicle_score', lambda _device_id: 42.5)
    monkeypatch.setattr(
        monitor_api,
        'get_recent_events',
        lambda **_kwargs: [{'timestamp': '2099-01-01T12:00:00'}],
    )

    response = _client().get('/api/monitors/1/vehicles')

    assert response.status_code == 200
    assert response.get_json() == [{
        'device_id': 'SIM-1000',
        'score_atual': 42.5,
        'status': 'critical',
        'total_eventos_hoje': 1,
    }]


def test_monitor_vehicles_reports_unavailable_instead_of_fake_defaults(monkeypatch):
    monkeypatch.setattr(
        monitor_api.monitor_db,
        'get_monitor_vehicles',
        lambda _monitor_id: [{'device_id': 'SIM-1000'}],
    )

    def unavailable_score(_device_id):
        raise RuntimeError('motor indisponível')

    monkeypatch.setattr(monitor_api, 'get_vehicle_score', unavailable_score)

    response = _client().get('/api/monitors/1/vehicles')

    assert response.status_code == 503
    assert response.get_json() == {
        'code': 'BEHAVIORAL_DATA_UNAVAILABLE',
        'error': 'Dados comportamentais temporariamente indisponíveis',
    }
    assert b'85' not in response.data


def test_event_stats_use_persisted_runtime_events_and_catalog(monkeypatch):
    monkeypatch.setattr(monitor_api, 'get_recent_events', lambda **_kwargs: [
        {'type': 'speeding', 'timestamp': '2099-01-01T12:00:00'},
        {'type': 'speeding', 'timestamp': '2099-01-01T12:01:00'},
    ])

    class Cursor:
        def execute(self, sql):
            assert sql == 'SELECT codigo, categoria FROM tipo_evento'

        def fetchall(self):
            return [{'codigo': 'speeding', 'categoria': 'behavioral'}]

        def close(self):
            pass

    class Connection:
        def cursor(self, dictionary=False):
            assert dictionary is True
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr(monitor_api.monitor_db, 'get_connection', Connection)
    monkeypatch.setattr(monitor_api, 'datetime', type('FixedDateTime', (), {
        'now': staticmethod(lambda: __import__('datetime').datetime(2099, 1, 1)),
        'fromisoformat': staticmethod(__import__('datetime').datetime.fromisoformat),
    }))

    response = _client().get('/api/events/stats')

    assert response.status_code == 200
    assert response.get_json() == {
        'total_eventos_hoje': 2,
        'por_tipo': {'speeding': 2},
        'por_categoria': {'behavioral': 2},
    }
