import pytest

from server.geofence_engine import (
    classify_with_hysteresis,
    effective_hysteresis_m,
    evolve_state,
    signed_distance_m,
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
