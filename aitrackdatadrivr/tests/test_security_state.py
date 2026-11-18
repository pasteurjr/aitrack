from pathlib import Path
import re

from flask import Flask
import pytest

from server import security_state_api, security_state_db


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '027_create_security_arming_state.sql'


def client():
    app = Flask(__name__)
    app.register_blueprint(security_state_api.security_state_bp)
    return app.test_client()


def payload(**overrides):
    value = {
        'target_state': 'armed', 'expected_version': 1,
        'actor': {'type': 'human', 'id': 'operator-1', 'name': 'Operador Um'},
        'authorization_basis': 'owner_request',
        'reason': 'Solicitação confirmada pelo proprietário',
        'correlation_id': 'transition-1',
    }
    value.update(overrides)
    return value


def test_migration_has_versioned_state_history_scope_and_no_destructive_sql():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.vehicle_security_state' in sql
    assert 'monitoramento.vehicle_security_history' in sql
    assert "enum('disarmed','armed')" in sql
    assert 'version int unsigned not null' in sql
    assert 'authorization_basis' in sql
    assert 'unique key uq_vehicle_security_correlation' in sql
    assert 'insert ignore' in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


@pytest.mark.parametrize('field,value,match', [
    ('target_state', 'unknown', 'target_state'),
    ('actor', {}, 'actor completo'),
    ('authorization_basis', 'agent_guess', 'authorization_basis'),
    ('reason', 'x', 'reason'),
    ('expected_version', 0, 'expected_version'),
])
def test_transition_rejects_unauthorized_or_incomplete_request(field, value, match):
    with pytest.raises(security_state_db.SecurityStateError, match=match):
        security_state_db.transition(1, payload(**{field: value}))


def test_authorization_basis_must_match_actor_type():
    with pytest.raises(security_state_db.SecurityStateError, match='actor system'):
        security_state_db.transition(1, payload(authorization_basis='scheduled_policy'))
    with pytest.raises(security_state_db.SecurityStateError, match='actor human'):
        security_state_db.transition(1, payload(
            actor={'type': 'system', 'id': 'scheduler', 'name': 'Scheduler'},
        ))


def test_get_api_returns_state_and_not_found(monkeypatch):
    state = {'schema_version': 'vehicle-security-state.v1', 'vehicle_id': 1, 'state': 'disarmed'}
    monkeypatch.setattr(security_state_api.security_state_db, 'get_state', lambda *_args: state)
    response = client().get('/api/vehicles/1/security-state')
    assert response.status_code == 200
    assert response.get_json()['state'] == 'disarmed'

    monkeypatch.setattr(security_state_api.security_state_db, 'get_state', lambda *_args: None)
    assert client().get('/api/vehicles/999/security-state').status_code == 404


def test_transition_api_maps_conflict_and_success(monkeypatch):
    monkeypatch.setattr(
        security_state_api.security_state_db, 'transition',
        lambda *_args: (_ for _ in ()).throw(
            security_state_db.SecurityStateConflict('Versão atual 2'),
        ),
    )
    conflict = client().post('/api/vehicles/1/security-state/transitions', json=payload())
    assert conflict.status_code == 409
    assert conflict.get_json()['code'] == 'SECURITY_STATE_VERSION_CONFLICT'

    monkeypatch.setattr(
        security_state_api.security_state_db, 'transition',
        lambda vehicle_id, body: {
            'schema_version': 'vehicle-security-state.v1', 'vehicle_id': vehicle_id,
            'state': body['target_state'], 'version': 2,
        },
    )
    success = client().post('/api/vehicles/1/security-state/transitions', json=payload())
    assert success.status_code == 200
    assert success.get_json()['state'] == 'armed'
