import json
from pathlib import Path

from server.audit_service import redact, record_event


class Cursor:
    lastrowid = 91
    def __init__(self): self.statement = None; self.params = None
    def execute(self, statement, params): self.statement = statement; self.params = params
    def close(self): pass


class Connection:
    def __init__(self): self.cursor_value = Cursor(); self.commits = 0; self.rollbacks = 0
    def cursor(self): return self.cursor_value
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1
    def close(self): pass


def test_redacts_nested_secrets_without_mutating_safe_fields():
    source = {'status': 'ok', 'token': 'secret', 'nested': [{'email': 'a@b.test'}]}
    assert redact(source) == {
        'status': 'ok', 'token': '[REDACTED]',
        'nested': [{'email': '[REDACTED]'}],
    }


def test_writer_joins_existing_transaction_and_redacts_snapshots():
    connection = Connection()
    event_id = record_event({
        'tenant_id': 7, 'actor_type': 'human', 'actor_public_id': 'u-1',
        'action': 'incident.resolve', 'resource_type': 'incident',
        'resource_public_id': '9', 'before': {'status': 'new', 'password': 'x'},
        'after': {'status': 'resolved', 'token': 'y'}, 'metadata': {},
    }, connection=connection)
    assert event_id == 91
    assert connection.commits == 0 and connection.rollbacks == 0
    serialized = ' '.join(str(value) for value in connection.cursor_value.params)
    assert 'secret' not in serialized and '"x"' not in serialized and '"y"' not in serialized
    assert serialized.count('[REDACTED]') == 2


def test_audit_schema_is_append_only_and_tenant_indexed():
    sql = (Path(__file__).parents[1] / 'migrations' / '065_create_audit_events.sql').read_text()
    assert 'idx_audit_tenant_time' in sql
    assert 'trg_audit_events_update' in sql
    assert 'trg_audit_events_delete' in sql
    assert "SIGNAL SQLSTATE '45000'" in sql
