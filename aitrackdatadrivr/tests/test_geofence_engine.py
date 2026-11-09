import pytest
from datetime import datetime

from server.geofence_engine import (
    classify_with_hysteresis,
    effective_hysteresis_m,
    evolve_state,
    signed_distance_m,
    schedule_is_active,
    active_window_start,
)


def _state_values(result):
    """Aceita o contrato como tupla, mapping ou objeto de estado nomeado."""
    fields = ('stable_state', 'pending_state', 'pending_samples', 'transition')
    if isinstance(result, dict):
        return tuple(result[field] for field in fields)
    if all(hasattr(result, field) for field in fields):
        return tuple(getattr(result, field) for field in fields)
    return tuple(result)


def test_signed_distance_for_circle_is_positive_inside_and_negative_outside():
    circle = {
        'type': 'Circle',
        'center': [0.0, 0.0],
        'radius_meters': 100.0,
    }

    assert signed_distance_m(circle, 0.0, 0.0) == pytest.approx(100.0, abs=0.5)
    assert signed_distance_m(circle, 0.001, 0.0) == pytest.approx(-11.2, abs=1.0)


def test_signed_distance_for_polygon_respects_inside_boundary_and_outside():
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [-0.001, -0.001],
            [0.001, -0.001],
            [0.001, 0.001],
            [-0.001, 0.001],
            [-0.001, -0.001],
        ]],
    }

    assert signed_distance_m(polygon, 0.0, 0.0) > 100.0
    assert signed_distance_m(polygon, 0.001, 0.0) == pytest.approx(0.0, abs=0.5)
    assert signed_distance_m(polygon, 0.002, 0.0) < -100.0


@pytest.mark.parametrize(
    ('distance', 'expected'),
    [
        (31.0, 'inside'),
        (30.0, 'inside'),
        (29.9, None),
        (0.0, None),
        (-29.9, None),
        (-30.0, 'outside'),
        (-31.0, 'outside'),
    ],
)
def test_classification_keeps_points_in_hysteresis_band_unclassified(distance, expected):
    assert classify_with_hysteresis(distance, hysteresis=30.0) == expected


def test_transition_requires_two_consecutive_samples():
    first = evolve_state('outside', None, 0, 'inside', confirmation_samples=2)
    assert _state_values(first) == ('outside', 'inside', 1, None)

    second = evolve_state(*_state_values(first)[:3], 'inside', confirmation_samples=2)
    assert _state_values(second) == ('inside', None, 0, ('outside', 'inside'))


def test_noise_restarts_transition_confirmation():
    first = evolve_state('outside', None, 0, 'inside', confirmation_samples=2)
    noise = evolve_state(*_state_values(first)[:3], 'outside', confirmation_samples=2)
    assert _state_values(noise) == ('outside', None, 0, None)

    restarted = evolve_state(*_state_values(noise)[:3], 'inside', confirmation_samples=2)
    assert _state_values(restarted) == ('outside', 'inside', 1, None)


def test_stable_candidate_does_not_duplicate_confirmed_transition():
    result = evolve_state('inside', None, 0, 'inside', confirmation_samples=2)

    assert _state_values(result) == ('inside', None, 0, None)


def test_gps_accuracy_expands_the_neutral_band():
    margin = effective_hysteresis_m(hysteresis=30.0, accuracy_m=20.0)

    assert margin == 50.0
    assert classify_with_hysteresis(40.0, margin) is None
    assert classify_with_hysteresis(51.0, margin) == 'inside'


def test_schedule_without_windows_is_always_active():
    assert schedule_is_active(
        datetime(2026, 11, 9, 3, 0), 'America/Sao_Paulo', [],
    )


def test_weekly_schedule_respects_timezone_and_end_exclusive():
    schedules = [{
        'day_of_week': 0, 'start_time': '08:00:00',
        'end_time': '18:00:00', 'crosses_midnight': False,
    }]
    assert schedule_is_active(datetime(2026, 11, 9, 8, 0), 'America/Sao_Paulo', schedules)
    assert not schedule_is_active(datetime(2026, 11, 9, 18, 0), 'America/Sao_Paulo', schedules)


def test_schedule_crossing_midnight_uses_previous_weekday():
    schedules = [{
        'day_of_week': 0, 'start_time': '22:00:00',
        'end_time': '06:00:00', 'crosses_midnight': True,
    }]
    assert schedule_is_active(datetime(2026, 11, 9, 23, 0), 'America/Sao_Paulo', schedules)
    assert schedule_is_active(datetime(2026, 11, 10, 5, 59), 'America/Sao_Paulo', schedules)
    assert not schedule_is_active(datetime(2026, 11, 10, 6, 0), 'America/Sao_Paulo', schedules)


def test_invalid_timezone_fails_closed():
    schedules = [{
        'day_of_week': 0, 'start_time': '08:00:00',
        'end_time': '18:00:00', 'crosses_midnight': False,
    }]
    assert not schedule_is_active(datetime(2026, 11, 9, 9, 0), 'Invalid/Zone', schedules)


def test_separate_daily_windows_have_distinct_episode_starts():
    schedules = [
        {'day_of_week': day, 'start_time': '08:00:00', 'end_time': '18:00:00',
         'crosses_midnight': False}
        for day in (0, 1)
    ]

    assert active_window_start(
        datetime(2026, 11, 9, 17, 59), 'America/Sao_Paulo', schedules,
    ) == datetime(2026, 11, 9, 8, 0)
    assert active_window_start(
        datetime(2026, 11, 10, 8, 5), 'America/Sao_Paulo', schedules,
    ) == datetime(2026, 11, 10, 8, 0)
