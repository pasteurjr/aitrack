from pathlib import Path
import pytest
from server.message_template_db import render_body, validate_schema

MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '047_create_message_templates.sql'
SCHEMA = {'owner': {'type': 'string', 'max_length': 30}, 'speed': {'type': 'number'}}


def test_render_is_strict_typed_and_deterministic():
    body = 'Olá {{ owner }}, velocidade {{speed}} km/h.'
    assert render_body(body, SCHEMA, {'owner': 'Ana', 'speed': 88.5}) == 'Olá Ana, velocidade 88.5 km/h.'
    with pytest.raises(ValueError, match='extras'):
        render_body(body, SCHEMA, {'owner': 'Ana', 'speed': 88, 'phone': 'x'})
    with pytest.raises(ValueError, match='Tipo incorreto'):
        render_body(body, SCHEMA, {'owner': 'Ana', 'speed': '88'})


def test_schema_tokens_and_control_characters_are_rejected():
    with pytest.raises(ValueError, match='divergem'):
        render_body('Olá {{owner}}', SCHEMA, {'owner': 'Ana', 'speed': 1})
    with pytest.raises(ValueError, match='Valor inválido'):
        render_body('{{owner}} {{speed}}', SCHEMA, {'owner': 'A\x00B', 'speed': 1})
    with pytest.raises(ValueError, match='Tipo inválido'):
        validate_schema({'x': {'type': 'object'}})


def test_migration_versions_content_and_allows_single_approved_version():
    sql = MIGRATION.read_text().lower()
    for token in ('message_templates','message_template_versions','content_sha256','variable_schema_json','locale','approved_template_id','uq_message_template_approved'):
        assert token in sql
    assert 'template version content is immutable' in sql
    assert 'template versions cannot be deleted' in sql
