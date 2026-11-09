from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '018_create_dirijabem_ingestion.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_adds_received_time_offset_and_idempotent_receipts():
    content = sql()
    assert 'ADD COLUMN IF NOT EXISTS received_at DATETIME(6) NOT NULL' in content
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.source_ingestion_offsets' in content
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.source_position_receipts' in content
    assert 'PRIMARY KEY (source_code, stream_name)' in content
    assert 'PRIMARY KEY (source_code, external_position_id)' in content


def test_migration_never_writes_source_schemas_or_deletes_data():
    content = sql().lower()
    assert 'tracker.' not in content
    assert 'dirijabem.' not in content
    assert 'delete from' not in content
    assert 'drop table' not in content
    assert 'truncate' not in content
    assert 'on delete cascade' not in content
