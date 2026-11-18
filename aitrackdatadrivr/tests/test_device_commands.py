from pathlib import Path
import re

from flask import Flask
import pytest

from server import device_command_api, device_command_db


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '030_create_device_command_contract.sql'
)


def client():
    app = Flask(__name__)
    app.register_blueprint(device_command_api.device_command_bp)
    return app.test_client()


def command_payload(**overrides):
    value = {
        'capability_code': 'remote_immobilization',
        'idempotency_key': 'operator-7:incident-9:immobilize',
        'correlation_id': 'incident-9',
        'reason': 'Veículo confirmado como roubado',
        'confirmation_text': 'CONFIRMAR BLOQUEIO',
        'payload': {'enabled': True},
        'timeout_seconds': 30,
    }
    value.update(overrides)
    return value


def test_migration_models_idempotency_confirmation_timeout_and_audit_safely():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.device_commands' in sql
    assert 'monitoramento.device_command_events' in sql
    assert 'unique key uq_device_command_idempotency' in sql
    assert "'acknowledged','nacked','timed_out'" in sql
    assert 'provider_message_id' in sql
    assert 'correlation_id' in sql
    assert 'json_valid(payload_json)' in sql
    assert 'on delete restrict' in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


@pytest.mark.parametrize(
    ('current', 'target', 'final'),
    [
        ('requested', 'queued', False),
        ('requested', 'timed_out', True),
        ('queued', 'sent', False),
        ('queued', 'timed_out', True),
        ('sent', 'acknowledged', True),
        ('sent', 'nacked', True),
        ('sent', 'timed_out', True),
    ],
)
def test_state_machine_allows_only_explicit_transitions(current, target, final):
    assert device_command_db.plan_transition(current, target) == {
        'from_status': current,
        'to_status': target,
        'final': final,
    }


@pytest.mark.parametrize(
    ('current', 'target'),
    [
        ('requested', 'acknowledged'),
        ('queued', 'acknowledged'),
        ('sent', 'queued'),
        ('acknowledged', 'sent'),
        ('nacked', 'sent'),
        ('timed_out', 'sent'),
    ],
)
def test_state_machine_rejects_skips_reversals_and_final_state_changes(current, target):
    with pytest.raises(device_command_db.CommandError):
        device_command_db.plan_transition(current, target)


def test_post_maps_unconfirmed_capability_to_safe_conflict(monkeypatch):
    monkeypatch.setattr(device_command_api.device_command_auth, 'authenticate', lambda *_: {})
    monkeypatch.setattr(
        device_command_api.device_command_db,
        'create_command',
        lambda *_args: (_ for _ in ()).throw(
            device_command_db.CommandUnsupported('Comando não confirmado')
        ),
    )

    response = client().post('/api/vehicles/1/commands', json=command_payload())

    assert response.status_code == 409
    assert response.get_json()['code'] == 'COMMAND_CAPABILITY_NOT_CONFIRMED'


def test_post_distinguishes_created_from_idempotent_replay(monkeypatch):
    monkeypatch.setattr(device_command_api.device_command_auth, 'authenticate', lambda *_: {})
    result = {'public_id': 'command-1', 'idempotent': False}
    monkeypatch.setattr(device_command_api.device_command_db, 'create_command', lambda *_: result)
    assert client().post('/api/vehicles/1/commands', json=command_payload()).status_code == 201

    result['idempotent'] = True
    replay = client().post('/api/vehicles/1/commands', json=command_payload())
    assert replay.status_code == 200
    assert replay.get_json()['public_id'] == 'command-1'


def test_get_exposes_versioned_trace_and_validates_limit(monkeypatch):
    monkeypatch.setattr(device_command_api.device_command_auth, 'authenticate', lambda *_: {})
    monkeypatch.setattr(
        device_command_api.device_command_db,
        'list_commands',
        lambda vehicle_id, limit: [{'vehicle_id': vehicle_id, 'limit': limit}],
    )

    response = client().get('/api/vehicles/8/commands?limit=12')
    assert response.status_code == 200
    assert response.get_json() == {
        'schema_version': 'device-commands.v1',
        'count': 1,
        'commands': [{'vehicle_id': 8, 'limit': 12}],
    }
    assert client().get('/api/vehicles/8/commands?limit=invalid').status_code == 400


def test_runtime_starts_command_timeout_worker():
    source = (Path(__file__).resolve().parents[1] / 'run.py').read_text(encoding='utf-8')
    assert 'Thread(target=run_timeout_worker' in source
    assert 'command_timeout_thread.start()' in source
