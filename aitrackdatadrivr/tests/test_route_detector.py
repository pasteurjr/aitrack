from pathlib import Path

from server.route_detector import distance_to_route_m, evolve_route_state, is_planned_stop

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'056_create_route_detection.sql'

def test_distance_and_hysteresis_require_two_confirmations():
    route = [[-46.63, -23.55], [-46.62, -23.55]]
    assert distance_to_route_m([-46.625, -23.55], route) < 1
    far = distance_to_route_m([-46.625, -23.56], route)
    assert far > 1000

    first = evolve_route_state(True, None, 0, far, 100, 0)
    assert first.transition is None and first.pending_samples == 1
    second = evolve_route_state(
        True, first.pending_on_route, first.pending_samples, far, 100, 0
    )
    assert second.transition == 'deviation'
    assert second.stable_on_route is False

    border = evolve_route_state(True, None, 0, 105, 100, 0, hysteresis=10)
    assert border.transition is None

def test_accuracy_expands_corridor_and_planned_stop_is_excluded():
    assert evolve_route_state(True, None, 0, 130, 100, 50).pending_on_route is None
    assert is_planned_stop(
        [0, 0], [{'longitude': 0, 'latitude': 0, 'radius_meters': 20}]
    )

def test_detection_schema_is_idempotent_and_episode_unique():
    sql = MIGRATION.read_text().lower()
    required_tokens = (
        'route_execution_states',
        'route_episodes',
        'route_position_receipts',
        'unplanned_stop',
        'uq_route_episode_active',
        'uq_route_position',
    )
    for token in required_tokens:
        assert token in sql
