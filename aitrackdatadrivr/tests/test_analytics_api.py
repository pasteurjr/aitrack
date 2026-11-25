from flask import Flask

from server import analytics_api


def make_client(monkeypatch):
    monkeypatch.setattr(
        analytics_api,
        'aggregate_behavior',
        lambda period, sources: {
            'period': period.public(),
            'sources': list(sources),
            'total_events': 0,
            'source_totals': {source: 0 for source in sources},
            'by_type': [],
            'by_vehicle': [],
        },
    )
    app = Flask(__name__)
    app.register_blueprint(analytics_api.analytics_bp)
    return app.test_client()


def test_behavior_api_returns_equal_previous_period(monkeypatch):
    response = make_client(monkeypatch).get(
        '/api/analytics/behavior',
        query_string={
            'from': '2026-11-24T00:00',
            'to': '2026-11-25T00:00',
            'timezone': 'America/Sao_Paulo',
            'sources': 'tracker,dirijabem',
            'comparison': 'previous',
        },
    )
    body = response.get_json()
    assert response.status_code == 200
    assert body['schema_version'] == 'behavior-analytics.v1'
    assert body['current']['period']['duration_seconds'] == body['comparison']['period']['duration_seconds']
    assert body['current']['sources'] == ['tracker', 'dirijabem']


def test_behavior_api_rejects_invalid_source(monkeypatch):
    response = make_client(monkeypatch).get(
        '/api/analytics/behavior',
        query_string={
            'from': '2026-11-24T00:00Z',
            'to': '2026-11-25T00:00Z',
            'sources': 'mock',
        },
    )
    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_ANALYTICS_FILTER'
