from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '017_create_geofence_transitions.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_creates_persistent_state_and_transition_events():
    content = sql()
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.geofence_target_states' in content
    assert 'CREATE TABLE IF NOT EXISTS monitoramento.geofence_events' in content
    assert 'stable_state' in content
    assert 'pending_samples' in content
    assert 'last_observed_at' in content


def test_state_is_isolated_per_assignment_and_canonical_subject():
    content = sql()
    assert 'uk_geofence_state_vehicle (assignment_id, vehicle_id)' in content
    assert 'uk_geofence_state_driver (assignment_id, driver_id)' in content
    assert 'chk_geofence_state_subject' in content
    assert 'REFERENCES monitoramento.geofence_assignments(id)' in content


def test_event_keeps_crossing_evidence_and_geometry_version():
    content = sql()
    for field in (
        'source_code', 'event_type', 'crossing_direction', 'rule_applied',
        'geometry_version_id', 'latitude', 'longitude', 'accuracy_m',
        'signed_distance_m', 'observed_at', 'details_json',
    ):
        assert re.search(rf'\b{field}\b', content)
    assert 'JSON_VALID(details_json)' in content


def test_migration_is_additive_and_does_not_write_source_databases():
    executable = '\n'.join(
        line for line in sql().splitlines()
        if not line.lstrip().startswith('--')
    )
    assert 'tracker.' not in executable
    assert 'dirijabem.' not in executable
    assert not re.search(
        r'(?im)^\s*(?:DROP|TRUNCATE|DELETE\s+FROM|UPDATE\s+\S+\s+SET)\b',
        executable,
    )
    assert 'ON DELETE CASCADE' not in executable
