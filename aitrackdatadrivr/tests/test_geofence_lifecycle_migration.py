from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '016_geofence_lifecycle.sql'


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_allows_reusing_historical_geometry_without_losing_hash_lookup():
    content = sql()
    assert 'DROP INDEX IF EXISTS uk_geofence_geometry_hash' in content
    assert 'ADD KEY idx_geofence_geometry_hash (geofence_id, geometry_hash)' in content


def test_creates_restrictive_audit_history_for_lifecycle_actions():
    content = sql()
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.geofence_audit_log' in content
    for action in ('created', 'updated', 'geometry_updated', 'archived'):
        assert action in content
    assert 'JSON_VALID(details_json)' in content
    assert 'ON DELETE RESTRICT' in content
    assert 'ON DELETE CASCADE' not in content


def test_never_writes_to_source_schemas_or_deletes_data():
    content = sql().lower()
    assert 'tracker.' not in content
    assert 'dirijabem.' not in content
    assert 'delete from' not in content
    assert 'drop table' not in content
