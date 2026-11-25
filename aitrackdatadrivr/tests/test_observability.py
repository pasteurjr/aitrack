import json
import logging
from pathlib import Path

from server.observability import JsonFormatter, MetricsRegistry
from server.technical_alerts import alert_plan


def test_metrics_use_only_normalized_route_method_and_status():
    registry = MetricsRegistry()
    registry.observe_http('get', '/api/incidents/<int:incident_id>', 200, 37)
    registry.observe_http('get', '/api/incidents/<int:incident_id>', 200, 70)
    snapshot = registry.snapshot()
    assert snapshot['http_requests_total'] == [{
        'method': 'GET', 'route': '/api/incidents/<int:incident_id>',
        'status': '200', 'count': 2,
    }]
    serialized = json.dumps(snapshot)
    assert 'vehicle_id' not in serialized and 'request_id' not in serialized


def test_json_log_redacts_secrets_and_keeps_correlation_fields():
    record = logging.LogRecord('test', logging.INFO, __file__, 1,
                               'failure token=hidden', (), None)
    record.request_id = 'req-1'; record.route = '/api/test'
    payload = json.loads(JsonFormatter().format(record))
    assert 'hidden' not in payload['message']
    assert payload['request_id'] == 'req-1' and payload['route'] == '/api/test'


def test_alert_plan_separates_degraded_outage_and_recovery():
    degraded = alert_plan({'component_key': 'ai_provider', 'status': 'degraded', 'critical': False})
    outage = alert_plan({'component_key': 'database', 'status': 'outage', 'critical': True})
    healthy = alert_plan({'component_key': 'database', 'status': 'healthy', 'critical': True})
    assert degraded['severity'] == 'warning'
    assert outage['severity'] == 'critical'
    assert healthy == {'action': 'recover'}


def test_technical_alert_schema_is_internal_and_tracks_recovery():
    sql = (Path(__file__).parents[1] / 'migrations' / '067_create_technical_alerts.sql').read_text()
    assert 'technical_alert_history' in sql
    assert "'recovered'" in sql
    assert 'phone' not in sql.casefold() and 'recipient' not in sql.casefold()
