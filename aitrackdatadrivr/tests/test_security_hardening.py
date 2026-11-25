import os
from pathlib import Path

from flask import Flask

from server.auth_api import _cookie_options
from server.auth_middleware import install_authentication
from scripts.security_audit import scan


def test_production_cookie_is_secure_even_without_override(monkeypatch):
    monkeypatch.setenv('AITRACK_OPERATION_MODE', 'production')
    monkeypatch.delenv('AITRACK_COOKIE_SECURE', raising=False)
    assert _cookie_options()['secure'] is True


def test_security_headers_and_500_redaction(monkeypatch):
    app = Flask(__name__)
    @app.get('/api/health/live')
    def failure():
        return {'error': 'database password=hidden'}, 500
    install_authentication(app)
    response = app.test_client().get('/api/health/live')
    assert response.status_code == 500
    assert 'hidden' not in response.get_data(as_text=True)
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert 'camera=()' in response.headers['Permissions-Policy']


def test_tracked_worktree_has_no_detected_production_secret():
    root = Path(__file__).resolve().parents[2]
    assert scan(root) == []
