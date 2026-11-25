"""Proteção padrão da API por sessão e CSRF."""

import hashlib
from uuid import uuid4

from flask import g, jsonify, request

from .auth_service import AuthenticationError, CsrfError, authenticate_session, validate_csrf
from .authz import AuthorizationError, require_permission, required_permission


PUBLIC_PATHS = {
    '/api/auth/login', '/api/auth/recover', '/api/auth/reset',
    '/api/health/live', '/api/health/ready', '/api/message-events/callback',
}
MUTATING_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


def install_authentication(app):
    @app.before_request
    def require_authentication():
        g.request_id = request.headers.get('X-Request-ID') or str(uuid4())
        if request.method == 'OPTIONS' or not request.path.startswith('/api/') or request.path in PUBLIC_PATHS:
            return None
        try:
            principal = authenticate_session(request.cookies.get('aitrack_session'))
            if request.method in MUTATING_METHODS:
                validate_csrf(principal, request.headers.get('X-CSRF-Token'))
            require_permission(principal, required_permission(request.path, request.method))
            g.auth = principal
            return None
        except AuthenticationError as exc:
            return jsonify({'code': 'AUTHENTICATION_REQUIRED', 'error': str(exc), 'request_id': g.request_id}), 401
        except CsrfError as exc:
            return jsonify({'code': 'CSRF_INVALID', 'error': str(exc), 'request_id': g.request_id}), 403
        except AuthorizationError as exc:
            return jsonify({'code': 'FORBIDDEN', 'error': str(exc), 'request_id': g.request_id}), 403

    @app.after_request
    def security_headers(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', str(uuid4()))
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response


def source_ip_hash(value):
    return hashlib.sha256(str(value or '').encode()).hexdigest()
