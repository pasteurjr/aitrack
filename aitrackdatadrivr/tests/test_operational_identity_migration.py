from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '010_create_unified_operational_identity.sql'
)


def migration_sql() -> str:
    return MIGRATION.read_text(encoding='utf-8')


def executable_sql() -> str:
    return '\n'.join(
        line for line in migration_sql().splitlines()
        if not line.lstrip().startswith('--')
    )


def test_creates_dedicated_operational_schema_idempotently():
    sql = executable_sql().upper()

    assert 'CREATE DATABASE IF NOT EXISTS MONITORAMENTO' in sql
    for table in (
        'FONTES_DADOS',
        'VEICULOS',
        'VEICULO_IDENTIDADES',
        'MOTORISTAS',
        'MOTORISTA_IDENTIDADES',
        'VEICULO_MOTORISTA_VINCULOS',
    ):
        assert f'CREATE TABLE IF NOT EXISTS MONITORAMENTO.{table}' in sql


def test_never_writes_to_source_schemas():
    sql = executable_sql()

    assert not re.search(
        r'(?i)\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|CREATE\s+TABLE)\s+'
        r'(?:tracker|dirijabem)\.',
        sql,
    )
    assert not re.search(r'(?i)\b(?:DROP|TRUNCATE)\b', sql)


def test_vehicle_and_driver_source_identities_are_not_conflated():
    sql = migration_sql()

    assert 'monitoramento.veiculo_identidades' in sql
    assert "ENUM('vehicle_id', 'device_id', 'plate')" in sql
    assert 'monitoramento.motorista_identidades' in sql
    assert "ENUM('driver_id', 'user_id', 'document')" in sql
    assert 'uk_veiculo_identidade_origem' in sql
    assert 'uk_motorista_identidade_origem' in sql


def test_driver_vehicle_assignment_is_temporal_and_auditable():
    sql = migration_sql()

    assert 'monitoramento.veiculo_motorista_vinculos' in sql
    assert 'valido_desde DATETIME(6) NOT NULL' in sql
    assert 'valido_ate DATETIME(6) NULL' in sql
    assert 'FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)' in sql
    assert 'FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)' in sql
    assert 'ON DELETE CASCADE' not in sql
