import os

from flask import Blueprint, g, jsonify, request

from .auth_middleware import source_ip_hash
from .auth_service import (
    AuthenticationError, login, request_password_reset, reset_password,
    revoke_session,
)


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _cookie_options(http_only=True):
    production = os.getenv('AITRACK_OPERATION_MODE', '').lower() == 'production'
    return {
        'httponly': http_only,
        'secure': production or os.getenv('AITRACK_COOKIE_SECURE', 'false').lower() == 'true',
        'samesite': 'Lax',
        'path': '/',
    }


@auth_bp.post('/login')
def auth_login():
    data = request.get_json(silent=True) or {}
    try:
        result = login(data.get('email'), data.get('password'), getattr(g, 'request_id', None), source_ip_hash(request.remote_addr))
        response = jsonify({'schema_version': 'auth-session.v1', 'user': result['user'], 'tenant': result['tenant'], 'roles': result['roles'], 'permissions': result['permissions'], 'expires_at': result['expires_at']})
        response.set_cookie('aitrack_session', result['token'], max_age=8 * 3600, **_cookie_options(True))
        response.set_cookie('aitrack_csrf', result['csrf'], max_age=8 * 3600, **_cookie_options(False))
        return response
    except AuthenticationError:
        return jsonify({'code': 'INVALID_CREDENTIALS', 'error': 'Credenciais inválidas'}), 401
    except ValueError as exc:
        return jsonify({'code': 'INVALID_LOGIN', 'error': str(exc)}), 400


@auth_bp.get('/me')
def me():
    principal = g.auth
    return jsonify({'schema_version': 'auth-session.v1', 'user': {
        'public_id': principal['user_public_id'], 'display_name': principal['display_name'], 'email': principal['email'],
    }, 'tenant': {'public_id': principal['tenant_public_id'], 'slug': principal['tenant_slug']},
    'roles': principal['roles'], 'permissions': principal['permissions'],
    'expires_at': principal['absolute_expires_at'].isoformat()})


@auth_bp.post('/logout')
def logout():
    revoke_session(g.auth)
    response = jsonify({'status': 'logged_out'})
    response.delete_cookie('aitrack_session', path='/')
    response.delete_cookie('aitrack_csrf', path='/')
    return response


@auth_bp.post('/recover')
def recover():
    data = request.get_json(silent=True) or {}
    token = request_password_reset(data.get('email'))
    body = {'status': 'accepted', 'message': 'Se a conta existir, as instruções serão enviadas.'}
    debug_recovery = os.getenv('AITRACK_RECOVERY_DEBUG_TOKEN', 'false').lower() == 'true'
    if token and debug_recovery and os.getenv('AITRACK_OPERATION_MODE', '').lower() != 'production':
        body['debug_token'] = token
    return jsonify(body), 202


@auth_bp.post('/reset')
def reset():
    data = request.get_json(silent=True) or {}
    try:
        reset_password(data.get('token'), data.get('password'))
        return jsonify({'status': 'password_reset'})
    except (AuthenticationError, ValueError) as exc:
        return jsonify({'code': 'INVALID_RESET', 'error': str(exc)}), 400
