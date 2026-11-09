from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / '015_create_geofence_assignments.sql'
)


def sql():
    return MIGRATION.read_text(encoding='utf-8')


def test_creates_groups_members_assignments_and_schedules():
    content = sql()
    for table in (
        'monitoring_groups', 'monitoring_group_members',
        'geofence_assignments', 'geofence_assignment_schedules',
    ):
        assert f'CREATE TABLE IF NOT EXISTS monitoramento.{table}' in content


def test_group_members_distinguish_vehicle_and_driver():
    content = sql()

    assert "member_type ENUM('vehicle','driver')" in content
    assert 'chk_group_member_exactly_one' in content
    assert 'REFERENCES monitoramento.veiculos(id)' in content
    assert 'REFERENCES monitoramento.motoristas(id)' in content


def test_assignment_accepts_exactly_one_canonical_target():
    content = sql()

    assert "target_type ENUM('vehicle','driver','group')" in content
    assert 'chk_geofence_assignment_exactly_one' in content
    assert 'REFERENCES monitoramento.monitoring_groups(id)' in content
    for unique_key in (
        'uk_geofence_assignment_vehicle',
        'uk_geofence_assignment_driver',
        'uk_geofence_assignment_group',
    ):
        assert unique_key in content


def test_assignment_has_operational_detection_policy():
    content = sql()

    for field in (
        'notify_on_entry', 'notify_on_exit', 'dwell_threshold_seconds',
        'hysteresis_meters', 'cooldown_seconds', 'priority', 'timezone_name',
        'effective_from', 'effective_to',
    ):
        assert re.search(rf'\b{field}\b', content)
    assert 'chk_geofence_assignment_hysteresis' in content


def test_schedule_supports_weekly_and_overnight_windows():
    content = sql()

    assert 'day_of_week TINYINT UNSIGNED NOT NULL' in content
    assert 'start_time TIME NOT NULL' in content
    assert 'end_time TIME NOT NULL' in content
    assert 'crosses_midnight BOOLEAN NOT NULL' in content
    assert 'chk_assignment_schedule_day' in content
    assert 'chk_assignment_schedule_range' in content


def test_migration_is_additive_and_source_independent():
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
    assert 'ON DELETE CASCADE' not in executable
