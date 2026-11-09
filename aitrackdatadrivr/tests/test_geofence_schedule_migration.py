from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '020_add_geofence_schedule_dwell.sql'


def test_adds_dwell_episode_state_and_event_type():
    content = MIGRATION.read_text(encoding='utf-8')
    assert 'violation_started_at DATETIME(6)' in content
    assert 'dwell_notified_at DATETIME(6)' in content
    assert "'geofence_dwell'" in content
    assert 'crossing_direction' in content and 'NULL' in content


def test_changes_only_operational_schema():
    content = MIGRATION.read_text(encoding='utf-8').lower()
    assert 'tracker.' not in content
    assert 'dirijabem.' not in content
    assert 'drop table' not in content
    assert 'truncate' not in content
