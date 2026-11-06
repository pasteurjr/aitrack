from datetime import datetime
from decimal import Decimal

from flask import Flask

from server import incident_api, incident_db


def _client():
    app = Flask(__name__)
    app.register_blueprint(incident_api.incident_bp)
    return app.test_client()


def test_lists_incidents_with_validated_filters_and_pagination(monkeypatch):
    captured = {}

    def fake_list(filters, limit, offset):
        captured.update(filters=filters, limit=limit, offset=offset)
        return ([{'id': 9, 'status': 'new'}], 1)

    monkeypatch.setattr(incident_api.incident_db, 'list_incidents', fake_list)
    response = _client().get(
        '/api/incidents?status=new&severity=high&primary_source=tracker'
        '&vehicle_id=2&monitor_id=3&assigned_to=operador&open_only=true'
        '&limit=25&offset=5'
    )

    assert response.status_code == 200
    assert response.get_json() == {
        'schema_version': 'incident-list.v1',
        'total': 1,
        'limit': 25,
        'offset': 5,
        'incidents': [{'id': 9, 'status': 'new'}],
    }
    assert captured == {
        'filters': {
            'status': 'new', 'severity': 'high', 'primary_source': 'tracker',
            'vehicle_id': 2, 'monitor_id': 3, 'assigned_to': 'operador',
            'open_only': True,
        },
        'limit': 25,
        'offset': 5,
    }


def test_rejects_invalid_filters_before_database_call(monkeypatch):
    database_call = monkeypatch.setattr(
        incident_api.incident_db,
        'list_incidents',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )

    response = _client().get('/api/incidents?status=inventado&limit=999')

    assert database_call is None
    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_INCIDENT_FILTER'


def test_rejects_ambiguous_open_only_value(monkeypatch):
    monkeypatch.setattr(
        incident_api.incident_db,
        'list_incidents',
        lambda *_args: (_ for _ in ()).throw(AssertionError('não deve consultar')),
    )

    response = _client().get('/api/incidents?open_only=talvez')

    assert response.status_code == 400
    assert response.get_json()['error'] == 'open_only deve ser booleano'


def test_returns_detail_with_timeline_or_not_found(monkeypatch):
    monkeypatch.setattr(
        incident_api.incident_db,
        'get_incident',
        lambda incident_id, timeline_limit: {
            'id': incident_id,
            'timeline': [{'id': 1}],
            'timeline_total': 1,
            'timeline_truncated': False,
            'requested_limit': timeline_limit,
        } if incident_id == 7 else None,
    )

    found = _client().get('/api/incidents/7?timeline_limit=10')
    missing = _client().get('/api/incidents/8')

    assert found.status_code == 200
    assert found.get_json()['schema_version'] == 'incident-detail.v1'
    assert found.get_json()['incident']['requested_limit'] == 10
    assert missing.status_code == 404
    assert missing.get_json()['code'] == 'INCIDENT_NOT_FOUND'


def test_database_failure_is_explicit_without_leaking_details(monkeypatch):
    monkeypatch.setattr(
        incident_api.incident_db,
        'list_incidents',
        lambda *_args: (_ for _ in ()).throw(RuntimeError('senha secreta')),
    )

    response = _client().get('/api/incidents')

    assert response.status_code == 500
    assert response.get_json()['code'] == 'INCIDENTS_UNAVAILABLE'
    assert b'senha secreta' not in response.data


def test_serializes_mysql_types_and_json_payloads():
    serialized = incident_db.serialize_record({
        'created_at': datetime(2026, 11, 6, 12, 0),
        'risk_score': Decimal('87.50'),
        'confidence': Decimal('0.9250'),
        'false_positive': 0,
        'context_snapshot': '{"speed": 91}',
        'details': 'json-invalido',
    })

    assert serialized == {
        'created_at': '2026-11-06T12:00:00',
        'risk_score': 87.5,
        'confidence': 0.925,
        'false_positive': False,
        'context_snapshot': {'speed': 91},
        'details': None,
    }


def test_repository_builds_filters_only_from_whitelist():
    where, params = incident_db._where_clause({
        'status': 'new',
        'vehicle_id': 4,
        'open_only': True,
        'malicious': "x' OR 1=1 --",
    })

    assert where == " WHERE i.status = %s AND i.vehicle_id = %s AND i.status NOT IN ('resolved', 'closed')"
    assert params == ['new', 4]
