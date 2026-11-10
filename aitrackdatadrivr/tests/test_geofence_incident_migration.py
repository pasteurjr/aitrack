from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '021_link_geofence_events_to_incidents.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_links_geofence_event_to_operational_incident():
    content = sql()

    assert 'ALTER TABLE monitoramento.geofence_target_states' in content
    assert 'violation_episode_id CHAR(36) NULL' in content
    assert 'ALTER TABLE monitoramento.geofence_events' in content
    assert 'context_vehicle_id BIGINT UNSIGNED NULL' in content
    assert 'incident_id BIGINT UNSIGNED NULL' in content
    assert "ENUM('pending','correlated','deferred','error')" in content
    assert 'correlation_attempts SMALLINT UNSIGNED' in content
    assert 'idx_geofence_events_episode (violation_episode_id)' in content
    assert 'idx_geofence_events_correlation' in content
    assert 'idx_geofence_events_incident (incident_id)' in content
    assert 'REFERENCES monitoramento.incidents(id)' in content
    assert 'REFERENCES monitoramento.veiculos(id)' in content
    assert 'ON DELETE RESTRICT' in content


def test_migration_never_writes_to_source_schemas_or_removes_data():
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
