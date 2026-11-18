from pathlib import Path
import re

from flask import Flask
import pytest

from server import device_command_api, device_command_auth, device_command_db


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '031_secure_critical_device_commands.sql'
)


def client():
    app = Flask(__name__)
    app.register_blueprint(device_command_api.device_command_bp)
    return app.test_client()


def principal(role='operator', principal_id=1):
    return {
        'id': principal_id,
        'public_id': f'{role}-{principal_id}',
        'display_name': f'{role.title()} {principal_id}',
        'role': role,
    }


def test_migration_requires_hashed_principal_policy_approval_and_immutable_fks():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.command_principals' in sql
    assert 'token_sha256 char(64)' in sql
    assert "enum('operator','supervisor','admin')" in sql
    assert 'monitoramento.command_authorization_policies' in sql
    assert 'required_approvals' in sql
    assert 'confirmation_text' in sql
    assert 'monitoramento.device_command_approvals' in sql
    assert 'unique key uq_command_approval_principal' in sql
    assert sql.count('on delete restrict') >= 4
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


@pytest.mark.parametrize('header', [None, '', 'Basic abc', 'Bearer short'])
def test_bearer_parser_fails_closed(header):
    with pytest.raises(device_command_auth.CommandAuthenticationError):
        device_command_auth.bearer_token(header)


def test_role_hierarchy_is_server_side():
    device_command_auth.require_role(principal('supervisor'), 'operator')
    device_command_auth.require_role(principal('admin'), 'supervisor')
    with pytest.raises(device_command_auth.CommandAuthorizationError):
        device_command_auth.require_role(principal('operator'), 'supervisor')


def test_command_api_requires_authentication_before_repository(monkeypatch):
    called = False

    def repository(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(device_command_api.device_command_db, 'create_command', repository)
    response = client().post('/api/vehicles/1/commands', json={})

    assert response.status_code == 401
    assert response.get_json()['code'] == 'COMMAND_AUTHENTICATION_REQUIRED'
    assert called is False


def test_identity_is_injected_from_token_not_accepted_from_payload():
    with pytest.raises(device_command_db.CommandError, match='actor não pode'):
        device_command_db.create_command(
            1,
            {
                'capability_code': 'remote_immobilization',
                'idempotency_key': 'critical-command-test',
                'correlation_id': 'incident-1',
                'actor': {'id': 'admin', 'role': 'admin'},
                'reason': 'Tentativa de falsificação de identidade',
                'confirmation_text': 'CONFIRMAR BLOQUEIO',
                'payload': {'enabled': True},
            },
            principal(),
        )


def test_authorization_endpoint_maps_role_denial_without_repository_leak(monkeypatch):
    monkeypatch.setattr(
        device_command_api.device_command_auth,
        'authenticate',
        lambda *_: principal('operator'),
    )
    monkeypatch.setattr(
        device_command_api.device_command_db,
        'decide_command',
        lambda *_args: (_ for _ in ()).throw(
            device_command_auth.CommandAuthorizationError('Papel supervisor é obrigatório')
        ),
    )

    response = client().post(
        '/api/vehicles/1/commands/command-1/authorization',
        headers={'Authorization': 'Bearer ' + 'x' * 32},
        json={},
    )

    assert response.status_code == 403
    assert response.get_json()['code'] == 'COMMAND_FORBIDDEN'


def test_authorization_endpoint_returns_approved_contract(monkeypatch):
    approver = principal('supervisor', 2)
    monkeypatch.setattr(device_command_api.device_command_auth, 'authenticate', lambda *_: approver)
    monkeypatch.setattr(
        device_command_api.device_command_db,
        'decide_command',
        lambda vehicle_id, public_id, payload, authenticated: {
            'vehicle_id': vehicle_id,
            'public_id': public_id,
            'status': 'queued',
            'approval_status': 'approved',
            'approver': authenticated['public_id'],
            'version': payload['expected_version'] + 1,
        },
    )
    response = client().post(
        '/api/vehicles/1/commands/command-1/authorization',
        headers={'Authorization': 'Bearer ' + 'x' * 32},
        json={
            'decision': 'approved',
            'reason': 'Protocolo confirmado pelo supervisor',
            'confirmation_text': 'CONFIRMAR BLOQUEIO',
            'correlation_id': 'approval-1',
            'expected_version': 1,
        },
    )

    assert response.status_code == 200
    assert response.get_json()['status'] == 'queued'
    assert response.get_json()['approver'] == 'supervisor-2'
