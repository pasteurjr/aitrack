from pathlib import Path

from server.health_service import sanitize_reason, status_from_age


def test_health_age_thresholds_are_deterministic():
    assert status_from_age(None, 60, 120) == 'unknown'
    assert status_from_age(59, 60, 120) == 'healthy'
    assert status_from_age(60, 60, 120) == 'degraded'
    assert status_from_age(120, 60, 120) == 'outage'


def test_health_reason_never_exposes_credentials():
    value = sanitize_reason(
        'token=abc password:xyz Authorization: Bearer bearer-value '
        'url=https://user:url-password@provider {"api_key":"json-value"}'
    )
    for secret in ('abc', 'xyz', 'bearer-value', 'url-password', 'json-value'):
        assert secret not in value
    assert value.count('[REDACTED]') >= 5


def test_health_schema_has_components_and_transition_history():
    sql = (Path(__file__).parents[1] / 'migrations' / '066_create_component_health.sql').read_text()
    for component in ('tracker_ingestion', 'dirijabem_ingestion', 'ai_provider',
                      'message_provider', 'voice_provider', 'action_worker', 'database'):
        assert component in sql
    assert 'health_transitions' in sql
