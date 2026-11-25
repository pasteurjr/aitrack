from flask import Flask

from server import health_api


def client():
    app = Flask(__name__)
    app.register_blueprint(health_api.health_bp)
    return app.test_client()


def test_public_readiness_contract_is_minimal(monkeypatch):
    monkeypatch.setattr(health_api, 'readiness', lambda: {
        'status': 'not_ready', 'database': True, 'blocker_count': 2,
    })
    response = client().get('/api/health/ready')
    assert response.status_code == 503
    assert response.get_json() == {
        'status': 'not_ready', 'database': True, 'blocker_count': 2,
    }
    assert 'components' not in response.get_json()


def test_detailed_health_validates_history_limit(monkeypatch):
    monkeypatch.setattr(health_api, 'integration_snapshot', lambda limit: {
        'schema_version': 'integration-health.v1', 'history_limit': limit,
    })
    assert client().get('/api/health/integrations?history_limit=10').get_json()['history_limit'] == 10
    invalid = client().get('/api/health/integrations?history_limit=101')
    assert invalid.status_code == 400
    assert invalid.get_json()['code'] == 'INVALID_HEALTH_FILTER'
