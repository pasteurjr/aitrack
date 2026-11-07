from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '012_create_operational_incidents.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_creates_operational_monitor_incident_and_timeline_tables():
    content = sql()
    for table in ('monitores', 'incidents', 'incident_timeline'):
        assert f'CREATE TABLE IF NOT EXISTS monitoramento.{table}' in content


def test_incident_references_canonical_vehicle_and_preserves_legacy_reference():
    content = sql()

    assert 'vehicle_id BIGINT UNSIGNED NOT NULL' in content
    assert 'legacy_vehicle_id INT NULL' in content
    assert 'REFERENCES monitoramento.veiculos(id)' in content
    assert 'REFERENCES tracker.veiculo_unificado' not in content


def test_timeline_does_not_create_foreign_key_to_source_event_table():
    content = sql()

    assert 'event_source VARCHAR(30) NULL' in content
    assert 'REFERENCES tracker.eventos' not in content
    assert 'REFERENCES monitoramento.incidents(id)' in content


def test_migration_is_additive_and_never_writes_to_sources():
    executable = '\n'.join(
        line for line in sql().splitlines()
        if not line.lstrip().startswith('--')
    )

    assert not re.search(
        r'(?i)\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|CREATE\s+TABLE)\s+'
        r'(?:tracker|dirijabem)\.',
        executable,
    )
    assert not re.search(r'(?i)\b(?:DROP|TRUNCATE)\b', executable)
