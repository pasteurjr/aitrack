from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '009_add_incident_detection_outcome.sql'
)


def test_detection_outcome_migration_is_scoped_and_idempotent():
    sql = MIGRATION.read_text(encoding='utf-8')

    assert 'ALTER TABLE tracker.incidents' in sql
    assert sql.count('IF NOT EXISTS') == 5
    assert 'DROP ' not in sql.upper()
    assert 'DELETE ' not in sql.upper()


def test_detection_outcome_covers_positive_and_negative_errors():
    sql = MIGRATION.read_text(encoding='utf-8')

    assert "'unreviewed', 'true_positive', 'false_positive', 'false_negative'" in sql
    assert 'classification_reason VARCHAR(50)' in sql
    assert 'classified_by VARCHAR(100)' in sql
    assert 'classified_at DATETIME(6)' in sql
    assert 'idx_incidents_detection_outcome' in sql
