from pathlib import Path
import hashlib
import hmac
import json

import pytest

from server.message_event_api import valid_signature
from server.message_event_db import normalize_status, parse_provider_timestamp, sanitize_metadata

MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '046_create_message_provider_events.sql'


@pytest.mark.parametrize(('raw', 'expected'), [
    ('queued', 'accepted'), ('submitted', 'sent'), ('delivered', 'delivered'),
    ('seen', 'read'), ('replied', 'responded'), ('undelivered', 'failed'),
    ('future-state', 'unknown'),
])
def test_provider_status_is_normalized_without_guessing(raw, expected):
    assert normalize_status(raw) == expected


def test_callback_metadata_is_allowlisted_and_timestamp_requires_timezone():
    payload = {
        'error_code': 'INVALID', 'reply_category': 'owner_confirmed',
        'phone': '+5511999999999', 'body': 'segredo', 'token': 'secret',
        'sandbox': True,
    }
    sanitized = sanitize_metadata(payload)
    assert sanitized == {
        'error_code': 'INVALID', 'reply_category': 'owner_confirmed', 'sandbox': True
    }
    assert parse_provider_timestamp('2026-11-19T23:10:00-03:00').isoformat() == '2026-11-20T02:10:00'
    with pytest.raises(ValueError, match='fuso'):
        parse_provider_timestamp('2026-11-19T23:10:00')


def test_webhook_signature_fails_closed_and_uses_constant_time_contract():
    raw = json.dumps({'status': 'delivered'}).encode()
    signature = hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
    assert valid_signature(raw, signature, 'test-secret')
    assert not valid_signature(raw, signature, '')
    assert not valid_signature(raw + b'x', signature, 'test-secret')


def test_migration_is_idempotent_append_only_and_deduplicated():
    sql = MIGRATION.read_text().lower()
    assert 'create table if not exists monitoramento.message_provider_events' in sql
    assert 'uq_message_provider_event' in sql
    assert 'payload_sha256' in sql and 'sanitized_metadata_json' in sql
    assert 'trg_message_provider_event_update' in sql
    assert 'trg_message_provider_event_delete' in sql
