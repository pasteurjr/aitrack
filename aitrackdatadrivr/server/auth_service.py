"""Senhas, sessões opacas, recuperação e eventos de segurança."""

from datetime import datetime, timedelta
import hashlib
import json
import re
import secrets
from uuid import uuid4

import bcrypt

from .monitor_db import get_connection


SESSION_IDLE_MINUTES = 30
SESSION_ABSOLUTE_HOURS = 8
RESET_MINUTES = 30
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class AuthenticationError(ValueError):
    pass


class CsrfError(ValueError):
    pass


def normalize_email(value):
    email = str(value or '').strip().casefold()
    if not EMAIL_RE.match(email):
        raise ValueError('E-mail inválido')
    return email


def validate_password(password):
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError('Senha deve possuir pelo menos 12 caracteres')
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        raise ValueError('Senha deve combinar letras e números')
    return password


def hash_password(password):
    return bcrypt.hashpw(validate_password(password).encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(str(password).encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(str(token).encode()).hexdigest()


def create_user(email, display_name, password, tenant_slug='default', connection=None):
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns:
            conn.start_transaction()
        email = normalize_email(email)
        name = str(display_name or '').strip()
        if len(name) < 2:
            raise ValueError('Nome é obrigatório')
        cursor.execute("SELECT id FROM monitoramento.tenants WHERE slug=%s AND status='active'", (tenant_slug,))
        tenant = cursor.fetchone()
        if not tenant:
            cursor.execute("INSERT INTO monitoramento.tenants(public_id,slug,name) VALUES(%s,%s,%s)", (str(uuid4()), tenant_slug, tenant_slug.title()))
            tenant = {'id': cursor.lastrowid}
        public_id = str(uuid4())
        cursor.execute(
            "INSERT INTO monitoramento.auth_users(public_id,email_normalized,display_name,password_hash) VALUES(%s,%s,%s,%s)",
            (public_id, email, name, hash_password(password)),
        )
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO monitoramento.auth_memberships(user_id,tenant_id,is_default) VALUES(%s,%s,TRUE)", (user_id, tenant['id']))
        if owns:
            conn.commit()
        return {'id': user_id, 'public_id': public_id, 'tenant_id': tenant['id']}
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def login(email, password, request_id=None, source_ip_hash=None, connection=None, now=None):
    current = now or datetime.utcnow()
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns:
            conn.start_transaction()
        try:
            normalized = normalize_email(email)
        except ValueError:
            normalized = ''
        cursor.execute("SELECT * FROM monitoramento.auth_users WHERE email_normalized=%s FOR UPDATE", (normalized,))
        user = cursor.fetchone()
        valid = bool(user and user['status'] == 'active' and (not user['locked_until'] or user['locked_until'] <= current) and verify_password(password, user['password_hash']))
        if not valid:
            if user and user['status'] == 'active':
                attempts = int(user['failed_attempts']) + 1
                locked = current + timedelta(minutes=LOCK_MINUTES) if attempts >= MAX_FAILED_ATTEMPTS else None
                cursor.execute("UPDATE monitoramento.auth_users SET failed_attempts=%s,locked_until=%s WHERE id=%s", (attempts, locked, user['id']))
            _security_event(cursor, user['id'] if user else None, None, 'login_failed', request_id, source_ip_hash, {})
            if owns:
                conn.commit()
            raise AuthenticationError('Credenciais inválidas')
        cursor.execute("""SELECT m.tenant_id,t.public_id tenant_public_id,t.slug tenant_slug
          FROM monitoramento.auth_memberships m JOIN monitoramento.tenants t ON t.id=m.tenant_id
          WHERE m.user_id=%s AND m.status='active' AND t.status='active'
          ORDER BY m.is_default DESC,m.id LIMIT 1""", (user['id'],))
        membership = cursor.fetchone()
        if not membership:
            raise AuthenticationError('Credenciais inválidas')
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        absolute = current + timedelta(hours=SESSION_ABSOLUTE_HOURS)
        idle = current + timedelta(minutes=SESSION_IDLE_MINUTES)
        session_public_id = str(uuid4())
        cursor.execute("""INSERT INTO monitoramento.auth_sessions(
          public_id,token_sha256,csrf_sha256,user_id,tenant_id,last_seen_at,idle_expires_at,absolute_expires_at)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
          (session_public_id, token_digest(token), token_digest(csrf), user['id'], membership['tenant_id'], current, idle, absolute))
        cursor.execute("UPDATE monitoramento.auth_users SET failed_attempts=0,locked_until=NULL,last_login_at=%s WHERE id=%s", (current, user['id']))
        _security_event(cursor, user['id'], membership['tenant_id'], 'login_succeeded', request_id, source_ip_hash, {'session_public_id': session_public_id})
        if owns:
            conn.commit()
        return {
            'token': token, 'csrf': csrf,
            'user': {'public_id': user['public_id'], 'display_name': user['display_name'], 'email': user['email_normalized']},
            'tenant': {'public_id': membership['tenant_public_id'], 'slug': membership['tenant_slug']},
            'expires_at': absolute.isoformat(),
        }
    except AuthenticationError:
        raise
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def authenticate_session(token, connection=None, now=None):
    if not token or len(token) < 32:
        raise AuthenticationError('Sessão obrigatória')
    current = now or datetime.utcnow()
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT s.*,u.public_id user_public_id,u.display_name,u.email_normalized,
          u.status user_status,t.public_id tenant_public_id,t.slug tenant_slug,t.status tenant_status
          FROM monitoramento.auth_sessions s
          JOIN monitoramento.auth_users u ON u.id=s.user_id
          JOIN monitoramento.tenants t ON t.id=s.tenant_id
          WHERE s.token_sha256=%s""", (token_digest(token),))
        row = cursor.fetchone()
        if not row or row['revoked_at'] or row['idle_expires_at'] <= current or row['absolute_expires_at'] <= current or row['user_status'] != 'active' or row['tenant_status'] != 'active':
            raise AuthenticationError('Sessão inválida ou expirada')
        new_idle = min(current + timedelta(minutes=SESSION_IDLE_MINUTES), row['absolute_expires_at'])
        cursor.execute("UPDATE monitoramento.auth_sessions SET last_seen_at=%s,idle_expires_at=%s WHERE id=%s", (current, new_idle, row['id']))
        if owns:
            conn.commit()
        return {
            'session_id': row['id'], 'session_public_id': row['public_id'],
            'csrf_sha256': row['csrf_sha256'], 'user_id': row['user_id'],
            'user_public_id': row['user_public_id'], 'display_name': row['display_name'],
            'email': row['email_normalized'], 'tenant_id': row['tenant_id'],
            'tenant_public_id': row['tenant_public_id'], 'tenant_slug': row['tenant_slug'],
            'absolute_expires_at': row['absolute_expires_at'],
        }
    finally:
        cursor.close()
        if owns:
            conn.close()


def validate_csrf(principal, csrf_token):
    if not csrf_token or not secrets.compare_digest(principal['csrf_sha256'], token_digest(csrf_token)):
        raise CsrfError('Token CSRF inválido')


def revoke_session(principal, reason='logout', connection=None):
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE monitoramento.auth_sessions SET revoked_at=CURRENT_TIMESTAMP(6),revoke_reason=%s WHERE id=%s AND revoked_at IS NULL", (reason, principal['session_id']))
        _security_event(cursor, principal['user_id'], principal['tenant_id'], 'logout', None, None, {'reason': reason})
        if owns:
            conn.commit()
    finally:
        cursor.close()
        if owns:
            conn.close()


def request_password_reset(email, connection=None, now=None):
    current = now or datetime.utcnow()
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    raw_token = None
    try:
        if owns:
            conn.start_transaction()
        try:
            normalized = normalize_email(email)
        except ValueError:
            normalized = ''
        cursor.execute("SELECT id FROM monitoramento.auth_users WHERE email_normalized=%s AND status='active'", (normalized,))
        user = cursor.fetchone()
        if user:
            raw_token = secrets.token_urlsafe(48)
            cursor.execute("INSERT INTO monitoramento.auth_password_reset_tokens(user_id,token_sha256,expires_at) VALUES(%s,%s,%s)", (user['id'], token_digest(raw_token), current + timedelta(minutes=RESET_MINUTES)))
            _security_event(cursor, user['id'], None, 'password_reset_requested', None, None, {})
        if owns:
            conn.commit()
        return raw_token
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def reset_password(token, new_password, connection=None, now=None):
    current = now or datetime.utcnow()
    password_hash = hash_password(new_password)
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns:
            conn.start_transaction()
        cursor.execute("SELECT * FROM monitoramento.auth_password_reset_tokens WHERE token_sha256=%s FOR UPDATE", (token_digest(token),))
        reset = cursor.fetchone()
        if not reset or reset['consumed_at'] or reset['expires_at'] <= current:
            raise AuthenticationError('Token de recuperação inválido ou expirado')
        cursor.execute("UPDATE monitoramento.auth_password_reset_tokens SET consumed_at=%s WHERE id=%s", (current, reset['id']))
        cursor.execute("UPDATE monitoramento.auth_users SET password_hash=%s,password_changed_at=%s,failed_attempts=0,locked_until=NULL,version=version+1 WHERE id=%s", (password_hash, current, reset['user_id']))
        cursor.execute("UPDATE monitoramento.auth_sessions SET revoked_at=%s,revoke_reason='password_reset' WHERE user_id=%s AND revoked_at IS NULL", (current, reset['user_id']))
        _security_event(cursor, reset['user_id'], None, 'password_reset_completed', None, None, {})
        if owns:
            conn.commit()
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def _security_event(cursor, user_id, tenant_id, event_type, request_id, source_ip_hash, details):
    cursor.execute("""INSERT INTO monitoramento.auth_security_events(
      user_id,tenant_id,event_type,request_id,source_ip_sha256,details_json)
      VALUES(%s,%s,%s,%s,%s,%s)""", (user_id, tenant_id, event_type, request_id, source_ip_hash, json.dumps(details)))
