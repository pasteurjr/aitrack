from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '007_create_incidents.sql'
)


def migration_sql() -> str:
    return MIGRATION.read_text(encoding='utf-8')


def test_incident_migration_is_additive_and_scoped_to_tracker():
    sql = migration_sql()
    executable = '\n'.join(
        line for line in sql.splitlines()
        if not line.lstrip().startswith('--')
    ).upper()

    assert 'CREATE TABLE IF NOT EXISTS TRACKER.INCIDENTS' in executable
    assert not re.search(
        r'(?m)^\s*(DROP|TRUNCATE|DELETE|UPDATE|INSERT)\b',
        executable,
    )


def test_incident_migration_has_operational_state_and_idempotency():
    sql = migration_sql()

    for status in (
        'new', 'triage', 'in_progress', 'waiting_response',
        'escalated', 'resolved', 'closed',
    ):
        assert f"'{status}'" in sql
    assert 'UNIQUE KEY uk_incidents_correlation (correlation_key)' in sql
    assert 'version INT UNSIGNED NOT NULL DEFAULT 1' in sql


def test_incident_migration_links_identity_and_monitor_without_cascade_delete():
    sql = migration_sql()

    assert 'REFERENCES tracker.veiculo_unificado(id)' in sql
    assert 'REFERENCES tracker.monitores(id) ON DELETE SET NULL' in sql
    assert 'FOREIGN KEY (vehicle_id)' in sql
    assert 'ON DELETE CASCADE' not in sql


def test_incident_migration_covers_sla_assignment_risk_and_resolution():
    sql = migration_sql()

    required_columns = (
        'severity', 'risk_score', 'sla_due_at', 'next_action_at',
        'assigned_type', 'assigned_to', 'hypothesis', 'confidence',
        'resolution_code', 'resolution_notes', 'false_positive',
        'latitude', 'longitude', 'position_observed_at',
    )
    for column in required_columns:
        assert re.search(rf'\b{column}\b', sql)
