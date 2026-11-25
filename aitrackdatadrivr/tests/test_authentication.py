from datetime import datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask, jsonify

from server.auth_service import hash_password, normalize_email, token_digest, validate_password, verify_password
from server import auth_middleware


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '062_create_authentication.sql'


def test_password_hash_is_salted_and_verifiable_without_plaintext():
    first = hash_password('SenhaMuitoForte123')
    second = hash_password('SenhaMuitoForte123')
    assert first != second
    assert 'SenhaMuitoForte123' not in first
    assert verify_password('SenhaMuitoForte123', first)
    assert not verify_password('SenhaErrada123', first)


def test_password_and_email_policy():
    assert normalize_email(' Operador@Exemplo.COM ') == 'operador@exemplo.com'
    for password in ('curta1', 'semnumerosuficiente', '123456789012'):
        with pytest.raises(ValueError):
            validate_password(password)


def test_tokens_are_stored_only_as_sha256():
    digest = token_digest('token-secreto-com-mais-de-trinta-e-dois-caracteres')
    assert len(digest) == 64
    assert 'token-secreto' not in digest


def test_auth_schema_has_expiry_recovery_membership_and_immutable_events():
    sql = MIGRATION.read_text().lower()
    for token in ('auth_users', 'auth_memberships', 'auth_sessions', 'idle_expires_at',
                  'absolute_expires_at', 'auth_password_reset_tokens',
                  'auth_security_events', 'trg_auth_event_update'):
        assert token in sql
    assert 'insert into monitoramento.auth_users' not in sql


def test_middleware_denies_anonymous_and_requires_csrf_for_mutation(monkeypatch):
    app = Flask(__name__)
    app.add_url_rule('/api/private', 'private_get', lambda: jsonify({'ok': True}), methods=['GET'])
    app.add_url_rule('/api/private', 'private_post', lambda: jsonify({'ok': True}), methods=['POST'])
    principal = {'csrf_sha256': token_digest('csrf-token')}
    monkeypatch.setattr(auth_middleware, 'authenticate_session', lambda token: principal if token == 'session-token' else (_ for _ in ()).throw(auth_middleware.AuthenticationError('no')))
    auth_middleware.install_authentication(app)
    client = app.test_client()
    assert client.get('/api/private').status_code == 401
    client.set_cookie('aitrack_session', 'session-token')
    assert client.get('/api/private').status_code == 200
    assert client.post('/api/private').status_code == 403
    assert client.post('/api/private', headers={'X-CSRF-Token': 'csrf-token'}).status_code == 200
