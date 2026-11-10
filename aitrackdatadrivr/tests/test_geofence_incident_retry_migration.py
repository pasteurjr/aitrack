from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '022_harden_geofence_incident_retry.sql'
)


def test_legacy_events_are_deferred_and_new_default_is_safe():
    content = MIGRATION.read_text(encoding='utf-8')

    assert "ENUM('pending','correlated','deferred','error','ignored')" in content
    assert "NOT NULL DEFAULT 'deferred'" in content
    assert 'next_correlation_at DATETIME(6) NULL' in content
    assert 'WHERE violation_episode_id IS NULL' in content
    assert "correlation_status = 'pending'" in content
