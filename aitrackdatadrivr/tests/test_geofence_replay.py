from server.geofence_engine import signed_distance_m
from server.geofence_replay import (
    ReplayMismatch,
    execute_replay,
    standard_scenarios,
    validate_replay,
)


def test_standard_replay_covers_circle_polygon_border_schedule_and_dwell():
    scenarios = standard_scenarios()

    assert [item.name for item in scenarios] == [
        'circle_allowed', 'polygon_forbidden', 'scheduled_forbidden_circle',
    ]
    assert {item.geometry['type'] for item in scenarios} == {'Circle', 'Polygon'}
    assert all(item.confirmation_samples == 2 for item in scenarios)
    assert all(item.dwell_threshold_seconds == 2 for item in scenarios)
    assert scenarios[2].schedules[0]['start_time'] == '08:00:00'
    assert any('neutral' in point.label for item in scenarios for point in item.points)
    assert any(
        expected.event_type == 'geofence_dwell'
        for item in scenarios for expected in item.expected_events
    )


def test_declared_neutral_points_are_inside_hysteresis_band():
    for scenario in standard_scenarios()[:2]:
        neutral_points = [point for point in scenario.points if 'neutral' in point.label]
        assert neutral_points
        for point in neutral_points:
            assert abs(signed_distance_m(
                scenario.geometry, point.longitude, point.latitude,
            )) < scenario.hysteresis_meters


def test_execute_replay_uses_fixed_clock_order_and_external_ids():
    scenario = standard_scenarios()[0]
    calls = []

    def evaluator(**payload):
        calls.append(payload)
        return []

    assert execute_replay(scenario, evaluator, 'proof') == []
    assert [item['received_at'] for item in calls] == sorted(
        item['received_at'] for item in calls
    )
    assert calls[0]['external_position_id'] == 'proof:circle_allowed:0'
    assert calls[-1]['external_position_id'] == 'proof:circle_allowed:7'


def test_validate_replay_rejects_missing_or_extra_event():
    scenario = standard_scenarios()[0]

    try:
        validate_replay(scenario, [])
    except ReplayMismatch as error:
        assert scenario.name in str(error)
    else:
        raise AssertionError('replay incompleto deveria falhar')
