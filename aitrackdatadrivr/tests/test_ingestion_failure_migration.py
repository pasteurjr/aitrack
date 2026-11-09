from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '019_create_ingestion_failures.sql'
)


def test_creates_retry_and_quarantine_audit_without_touching_sources():
    content = MIGRATION.read_text(encoding='utf-8')
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.source_ingestion_failures' in content
    assert "status ENUM('retry','quarantined')" in content
    assert 'attempts SMALLINT UNSIGNED' in content
    assert 'dirijabem.' not in content.lower()
    assert 'tracker.' not in content.lower()
    assert 'ON DELETE CASCADE' not in content
