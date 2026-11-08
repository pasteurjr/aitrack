from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '013_create_operational_monitor_targets.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_creates_targets_analyses_and_alerts_in_operational_schema():
    content = sql()
    for table in ('monitor_targets', 'monitor_analises', 'monitor_alertas'):
        assert f'CREATE TABLE IF NOT EXISTS monitoramento.{table}' in content


def test_target_requires_exactly_one_vehicle_or_driver():
    content = sql()

    assert "target_type ENUM('vehicle','driver')" in content
    assert 'chk_monitor_target_exactly_one' in content
    assert "target_type = 'vehicle' AND vehicle_id IS NOT NULL AND driver_id IS NULL" in content
    assert "target_type = 'driver' AND driver_id IS NOT NULL AND vehicle_id IS NULL" in content


def test_targets_reference_only_canonical_entities():
    content = sql()

    assert 'REFERENCES monitoramento.veiculos(id)' in content
    assert 'REFERENCES monitoramento.motoristas(id)' in content
    assert 'REFERENCES monitoramento.monitores(id)' in content
    assert 'REFERENCES tracker.' not in content


def test_migration_never_writes_to_source_schemas():
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
