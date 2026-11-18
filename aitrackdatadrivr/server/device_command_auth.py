"""Autenticação isolada do canal crítico; identidade nunca vem do payload."""

import hashlib
from typing import Optional

from .monitor_db import get_connection


ROLE_RANK = {'operator': 1, 'supervisor': 2, 'admin': 3}


class CommandAuthenticationError(ValueError):
    code = 'COMMAND_AUTHENTICATION_REQUIRED'


class CommandAuthorizationError(ValueError):
    code = 'COMMAND_FORBIDDEN'


def bearer_token(authorization_header: Optional[str]) -> str:
    scheme, separator, token = (authorization_header or '').partition(' ')
    if separator != ' ' or scheme.lower() != 'bearer' or len(token.strip()) < 32:
        raise CommandAuthenticationError('Bearer token de comando é obrigatório')
    return token.strip()


def authenticate(authorization_header: Optional[str]) -> dict:
    digest = hashlib.sha256(bearer_token(authorization_header).encode('utf-8')).hexdigest()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id,public_id,display_name,role FROM monitoramento.command_principals "
            "WHERE token_sha256=%s AND active=TRUE AND revoked_at IS NULL",
            (digest,),
        )
        principal = cursor.fetchone()
        if not principal:
            raise CommandAuthenticationError('Credencial de comando inválida ou revogada')
        return principal
    finally:
        cursor.close()
        conn.close()


def require_role(principal: dict, required_role: str):
    if ROLE_RANK.get(principal.get('role'), 0) < ROLE_RANK.get(required_role, 99):
        raise CommandAuthorizationError(f'Papel {required_role} é obrigatório')
