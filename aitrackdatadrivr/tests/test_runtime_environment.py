from datetime import datetime, timezone

from flask import Flask

from server.runtime_api import runtime_bp
from server.runtime_environment import build_runtime_environment


NOW = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)


def test_simulation_is_authoritative_and_safe_with_unconfigured_sources():
    result = build_runtime_environment(
        {'AITRACK_OPERATION_MODE': 'simulation'}, generated_at=NOW,
    )

    assert result['mode'] == 'simulation'
    assert result['authority'] == 'global_configuration'
    assert result['safe_for_real_actions'] is False
    assert [source['mode'] for source in result['sources']] == ['unknown', 'unknown']


def test_replay_can_be_derived_from_both_sources():
    result = build_runtime_environment({
        'AITRACK_TRACKER_MODE': 'replay',
        'AITRACK_DIRIJABEM_MODE': 'replay',
    }, generated_at=NOW)

    assert result['mode'] == 'replay'
    assert result['authority'] == 'source_configuration'


def test_production_requires_global_and_both_sources_live():
    confirmed = build_runtime_environment({
        'AITRACK_OPERATION_MODE': 'production',
        'AITRACK_TRACKER_MODE': 'live',
        'AITRACK_DIRIJABEM_MODE': 'live',
    }, generated_at=NOW)
    unconfirmed = build_runtime_environment({
        'AITRACK_OPERATION_MODE': 'production',
        'AITRACK_TRACKER_MODE': 'live',
    }, generated_at=NOW)
    missing_global = build_runtime_environment({
        'AITRACK_TRACKER_MODE': 'live',
        'AITRACK_DIRIJABEM_MODE': 'live',
    }, generated_at=NOW)

    assert confirmed['mode'] == 'production'
    assert confirmed['safe_for_real_actions'] is True
    assert unconfirmed['mode'] == 'unknown'
    assert unconfirmed['safe_for_real_actions'] is False
    assert 'PRODUCTION_SOURCES_UNCONFIRMED' in unconfirmed['issues']
    assert missing_global['mode'] == 'unknown'
    assert 'PRODUCTION_GLOBAL_UNCONFIRMED' in missing_global['issues']


def test_conflicting_sources_are_reported_as_mixed():
    result = build_runtime_environment({
        'AITRACK_OPERATION_MODE': 'production',
        'AITRACK_TRACKER_MODE': 'live',
        'AITRACK_DIRIJABEM_MODE': 'replay',
    }, generated_at=NOW)

    assert result['mode'] == 'mixed'
    assert result['safe_for_real_actions'] is False
    assert 'GLOBAL_SOURCE_MODE_CONFLICT' in result['issues']


def test_missing_or_invalid_configuration_never_claims_production():
    missing = build_runtime_environment({}, generated_at=NOW)
    invalid = build_runtime_environment({
        'AITRACK_OPERATION_MODE': 'prod',
        'AITRACK_TRACKER_MODE': 'invalid',
    }, generated_at=NOW)

    assert missing['mode'] == 'unknown'
    assert invalid['mode'] == 'unknown'
    assert missing['safe_for_real_actions'] is False
    assert invalid['safe_for_real_actions'] is False
    assert 'INVALID_GLOBAL_MODE' in invalid['issues']


def test_runtime_endpoint_exposes_versioned_contract(monkeypatch):
    monkeypatch.setenv('AITRACK_OPERATION_MODE', 'simulation')
    monkeypatch.delenv('AITRACK_TRACKER_MODE', raising=False)
    monkeypatch.delenv('AITRACK_DIRIJABEM_MODE', raising=False)
    app = Flask(__name__)
    app.register_blueprint(runtime_bp)

    response = app.test_client().get('/api/runtime/environment')

    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    payload = response.get_json()
    assert payload['schema_version'] == 'runtime-environment.v1'
    assert payload['mode'] == 'simulation'
    assert payload['safe_for_real_actions'] is False
