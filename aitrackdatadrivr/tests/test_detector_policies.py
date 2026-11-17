from pathlib import Path
import re

from flask import Flask
import pytest

from server import detector_policy_api, detector_policy_db


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '025_create_detector_policies.sql'


def client():
    app = Flask(__name__)
    app.register_blueprint(detector_policy_api.detector_policy_bp)
    return app.test_client()


def payload(**overrides):
    value = {
        'policy_key': 'external-power-loss',
        'detector_type': 'threshold',
        'capability_code': 'external_voltage',
        'scope_type': 'global',
        'scope_ref': '*',
        'parameters': {'trigger_below_v': 11.5, 'recover_above_v': 12.2},
        'created_by': 'tester',
        'change_reason': 'Validação inicial',
    }
    value.update(overrides)
    return value


def test_migration_versions_scopes_limits_and_audit_without_destructive_sql():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.detector_policies' in sql
    assert 'monitoramento.detector_policy_audit' in sql
    assert 'unique key uq_detector_policy_version' in sql
    assert 'unique key uq_detector_policy_active' in sql
    assert "enum('global','source','monitor','vehicle')" in sql
    assert 'parameters_json longtext not null' in sql
    assert 'json_valid(parameters_json)' in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


def test_validation_requires_explicit_scope_actor_reason_and_parameters():
    assert detector_policy_db._validate(payload())['policy_key'] == 'external-power-loss'
    with pytest.raises(ValueError, match='scope_ref'):
        detector_policy_db._validate(payload(scope_type='vehicle', scope_ref='*'))
    with pytest.raises(ValueError, match='created_by'):
        detector_policy_db._validate(payload(created_by=''))
    with pytest.raises(ValueError, match='parameters'):
        detector_policy_db._validate(payload(parameters={}))


def test_list_api_exposes_versioned_contract(monkeypatch):
    monkeypatch.setattr(
        detector_policy_api.detector_policy_db,
        'list_policies',
        lambda status: [{'id': 1, 'status': status or 'draft'}],
    )

    response = client().get('/api/detector-policies?status=active')

    assert response.status_code == 200
    assert response.get_json() == {
        'schema_version': 'detector-policies.v1',
        'count': 1,
        'policies': [{'id': 1, 'status': 'active'}],
    }


def test_create_api_rejects_invalid_and_returns_created(monkeypatch):
    monkeypatch.setattr(
        detector_policy_api.detector_policy_db,
        'create_policy',
        lambda body: (_ for _ in ()).throw(ValueError('parameters inválido')),
    )
    invalid = client().post('/api/detector-policies', json={})
    assert invalid.status_code == 400
    assert invalid.get_json()['code'] == 'INVALID_DETECTOR_POLICY'

    monkeypatch.setattr(
        detector_policy_api.detector_policy_db,
        'create_policy',
        lambda body: {'id': 9, 'policy_key': body['policy_key'], 'version_number': 1},
    )
    created = client().post('/api/detector-policies', json=payload())
    assert created.status_code == 201
    assert created.get_json()['version_number'] == 1


def test_activation_api_has_explicit_not_found_and_success(monkeypatch):
    monkeypatch.setattr(
        detector_policy_api.detector_policy_db,
        'activate_policy',
        lambda *_args: (_ for _ in ()).throw(LookupError('Política não encontrada')),
    )
    missing = client().post(
        '/api/detector-policies/99/activate',
        json={'actor': 'tester', 'reason': 'Ativar'},
    )
    assert missing.status_code == 404

    monkeypatch.setattr(
        detector_policy_api.detector_policy_db,
        'activate_policy',
        lambda policy_id, actor, reason, correlation: {
            'id': policy_id, 'status': 'active', 'created_by': actor,
        },
    )
    activated = client().post(
        '/api/detector-policies/9/activate',
        json={'actor': 'tester', 'reason': 'Ativar', 'correlation_id': 'change-1'},
    )
    assert activated.status_code == 200
    assert activated.get_json()['status'] == 'active'
