"""Templates de mensagem: versão imutável, aprovação e render estrito."""

import hashlib
import json
import re

from .monitor_db import get_connection

TOKEN = re.compile(r'{{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*}}')
TYPES = {'string', 'integer', 'number', 'boolean'}


def validate_schema(schema):
    if not isinstance(schema, dict) or len(schema) > 30:
        raise ValueError('variable_schema deve ser objeto com até 30 variáveis')
    clean = {}
    for name, rule in schema.items():
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,49}', str(name)):
            raise ValueError(f'Nome de variável inválido: {name}')
        if not isinstance(rule, dict) or rule.get('type') not in TYPES:
            raise ValueError(f'Tipo inválido para {name}')
        max_length = rule.get('max_length', 500)
        if not isinstance(max_length, int) or not 1 <= max_length <= 2000:
            raise ValueError(f'max_length inválido para {name}')
        clean[name] = {
            'type': rule['type'], 'required': rule.get('required', True),
            'max_length': max_length,
        }
    return clean


def render_body(body, schema, variables):
    clean_schema = validate_schema(schema)
    if not isinstance(variables, dict):
        raise ValueError('variables deve ser objeto')
    tokens = set(TOKEN.findall(body))
    if tokens != set(clean_schema):
        raise ValueError('Tokens do corpo divergem do schema')
    extra = set(variables) - set(clean_schema)
    missing = {name for name, rule in clean_schema.items() if rule['required'] and name not in variables}
    if extra or missing:
        raise ValueError(f'Variáveis extras={sorted(extra)} ausentes={sorted(missing)}')

    rendered = {}
    for name, rule in clean_schema.items():
        value = variables.get(name, '')
        expected = rule['type']
        valid = (
            (expected == 'string' and isinstance(value, str))
            or (expected == 'integer' and isinstance(value, int) and not isinstance(value, bool))
            or (expected == 'number' and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (expected == 'boolean' and isinstance(value, bool))
        )
        if not valid:
            raise ValueError(f'Tipo incorreto para {name}')
        text = str(value).lower() if isinstance(value, bool) else str(value)
        if len(text) > rule['max_length'] or any(ord(char) < 32 and char not in '\n\t' for char in text):
            raise ValueError(f'Valor inválido para {name}')
        rendered[name] = text
    result = TOKEN.sub(lambda match: rendered[match.group(1)], body)
    if not result.strip() or len(result) > 5000:
        raise ValueError('Mensagem renderizada vazia ou acima de 5000 caracteres')
    return result


def create_template_version(payload):
    key = str(payload.get('template_key') or '').strip()
    name = str(payload.get('name') or '').strip()
    locale = str(payload.get('locale') or '').strip()
    channel = payload.get('channel')
    body = str(payload.get('body') or '')
    actor = str(payload.get('created_by') or '').strip()
    schema = validate_schema(payload.get('variable_schema'))
    if not re.fullmatch(r'[a-z][a-z0-9_.-]{2,99}', key) or not name or not locale or not actor:
        raise ValueError('template_key, name, locale e created_by inválidos')
    if channel not in {'sms', 'whatsapp', 'push', 'generic'}:
        raise ValueError('channel inválido')
    render_body(body, schema, {n: _example(r['type']) for n, r in schema.items()})
    canonical = json.dumps(schema, separators=(',', ':'), sort_keys=True)
    digest = hashlib.sha256(f'{locale}\0{channel}\0{body}\0{canonical}'.encode()).hexdigest()
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("SELECT id FROM monitoramento.message_templates WHERE template_key=%s FOR UPDATE", (key,))
        template = cursor.fetchone()
        if not template:
            cursor.execute("INSERT INTO monitoramento.message_templates(template_key,name) VALUES(%s,%s)", (key, name))
            template_id = cursor.lastrowid
        else:
            template_id = template['id']
        cursor.execute("SELECT COALESCE(MAX(version_no),0)+1 next_version FROM monitoramento.message_template_versions WHERE template_id=%s", (template_id,))
        version = cursor.fetchone()['next_version']
        cursor.execute("""INSERT INTO monitoramento.message_template_versions
          (template_id,version_no,locale,channel,body,variable_schema_json,content_sha256,created_by)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""", (template_id, version, locale, channel, body, canonical, digest, actor))
        version_id = cursor.lastrowid
        conn.commit()
        return {'id': version_id, 'template_id': template_id, 'version': version, 'status': 'draft', 'content_sha256': digest}
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()


def _example(expected):
    return {'string': 'x', 'integer': 1, 'number': 1.0, 'boolean': True}[expected]


def approve_template_version(version_id, actor):
    if not isinstance(version_id, int) or not str(actor).strip():
        raise ValueError('version_id e actor obrigatórios')
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("SELECT * FROM monitoramento.message_template_versions WHERE id=%s FOR UPDATE", (version_id,))
        row = cursor.fetchone()
        if not row: raise LookupError('Versão não encontrada')
        if row['status'] == 'approved': conn.commit(); return {'id': version_id, 'status': 'approved', 'idempotent_replay': True}
        if row['status'] != 'draft': raise ValueError('Somente draft pode ser aprovado')
        cursor.execute("UPDATE monitoramento.message_template_versions SET status='superseded' WHERE template_id=%s AND status='approved'", (row['template_id'],))
        cursor.execute("UPDATE monitoramento.message_template_versions SET status='approved',approved_by=%s,approved_at=CURRENT_TIMESTAMP(6) WHERE id=%s", (actor, version_id))
        conn.commit(); return {'id': version_id, 'status': 'approved', 'idempotent_replay': False}
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()


def preview_template_version(version_id, variables, require_approved=False):
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id,version_no,locale,channel,body,variable_schema_json,status,content_sha256 FROM monitoramento.message_template_versions WHERE id=%s", (version_id,))
        row = cursor.fetchone()
        if not row: raise LookupError('Versão não encontrada')
        if require_approved and row['status'] != 'approved':
            raise ValueError('Envio exige template aprovado')
        return {**{k: row[k] for k in ('id','version_no','locale','channel','status','content_sha256')}, 'rendered_body': render_body(row['body'], json.loads(row['variable_schema_json']), variables)}
    finally:
        cursor.close(); conn.close()
