from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '008_create_incident_timeline.sql'
)


def migration_sql() -> str:
    return MIGRATION.read_text(encoding='utf-8')


def executable_sql() -> str:
    return '\n'.join(
        line for line in migration_sql().splitlines()
        if not line.lstrip().startswith('--')
    )


def test_timeline_migration_is_additive_and_scoped():
    sql = executable_sql().upper()

    assert 'CREATE TABLE IF NOT EXISTS TRACKER.INCIDENT_TIMELINE' in sql
    assert not re.search(
        r'(?m)^\s*(DROP|TRUNCATE|DELETE|UPDATE|INSERT)\b',
        sql,
    )


def test_timeline_is_idempotent_and_ordered_per_incident():
    sql = migration_sql()

    assert 'UNIQUE KEY uk_incident_timeline_idempotency (idempotency_key)' in sql
    assert 'idx_incident_timeline_order (incident_id, occurred_at, id)' in sql
    assert 'updated_at' not in sql


def test_timeline_records_actor_transition_evidence_and_causality():
    sql = migration_sql()
    required_columns = (
        'actor_type', 'actor_id', 'actor_name', 'from_status', 'to_status',
        'event_id', 'evidence_type', 'evidence_ref', 'correlation_id',
        'causation_id', 'occurred_at', 'recorded_at', 'details', 'visibility',
    )

    for column in required_columns:
        assert re.search(rf'\b{column}\b', sql)


def test_timeline_preserves_incident_and_allows_event_retention_policy():
    sql = migration_sql()

    assert 'REFERENCES tracker.incidents(id)' in sql
    assert 'REFERENCES tracker.eventos(id) ON DELETE SET NULL' in sql
    assert 'incident_id) REFERENCES tracker.incidents(id) ON DELETE CASCADE' not in sql
