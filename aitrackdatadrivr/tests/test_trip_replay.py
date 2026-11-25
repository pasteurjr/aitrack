from datetime import datetime, timedelta
from pathlib import Path

import pytest

from server.trip_replay import merge_timeline, validate_speed


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '057_add_route_replay_positions.sql'


def test_merge_timeline_has_stable_order_without_changing_timestamps():
    instant = datetime(2026, 11, 25, 1, 0)
    later = instant + timedelta(seconds=1)
    result = merge_timeline(
        [{'kind': 'position', 'stable_id': 'p2', 'occurred_at': later}],
        [{'kind': 'episode_started', 'stable_id': 'e1', 'occurred_at': instant}],
        [{'kind': 'execution', 'stable_id': 'x1', 'occurred_at': instant}],
        [{'kind': 'position', 'stable_id': 'p1', 'occurred_at': instant}],
    )
    assert [item['stable_id'] for item in result] == ['x1', 'p1', 'e1', 'p2']
    assert result[-1]['occurred_at'] is later


@pytest.mark.parametrize('speed', [0.5, 1, 2, 4])
def test_validate_speed_accepts_only_replay_presets(speed):
    assert validate_speed(speed) == float(speed)


def test_validate_speed_rejects_unsafe_or_unknown_values():
    for value in (0, -1, 3, 8):
        with pytest.raises(ValueError):
            validate_speed(value)


def test_replay_migration_adds_coordinates_and_bounded_index():
    sql = MIGRATION.read_text().lower()
    for token in ('longitude', 'latitude', 'speed_kmh', 'idx_route_position_time'):
        assert token in sql
