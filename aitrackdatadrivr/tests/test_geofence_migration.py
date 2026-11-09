from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '014_create_geofences.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_creates_shared_geofences_and_immutable_geometry_versions():
    content = sql()

    assert 'CREATE TABLE IF NOT EXISTS monitoramento.geofences' in content
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.geofence_versions' in content
    assert "geometry_type ENUM('circle','polygon')" in content
    assert 'geometry GEOMETRY NOT NULL' in content
    assert 'UNIQUE KEY uk_geofence_version (geofence_id, version_number)' in content


def test_supports_allowed_forbidden_lifecycle_and_ownership():
    content = sql()

    assert "regra ENUM('allowed','forbidden')" in content
    assert "status ENUM('draft','active','inactive','archived')" in content
    for field in ('owner_ref', 'criado_por', 'atualizado_por', 'version'):
        assert re.search(rf'\b{field}\b', content)


def test_circle_and_polygon_constraints_are_explicit():
    content = sql()

    assert 'radius_meters DECIMAL(10,2) NULL' in content
    assert 'chk_geofence_version_radius' in content
    assert "geometry_type = 'circle' AND radius_meters IS NOT NULL" in content
    assert "geometry_type = 'polygon' AND radius_meters IS NULL" in content
    assert 'SPATIAL KEY idx_geofence_versions_geometry (geometry)' in content


def test_versions_are_auditable_and_never_cascade_deleted():
    content = sql()

    for field in (
        'geometry_hash', 'change_reason', 'created_by', 'valid_from',
        'valid_to', 'created_at',
    ):
        assert re.search(rf'\b{field}\b', content)
    assert 'ON DELETE RESTRICT' in content
    assert 'ON DELETE CASCADE' not in content


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
