import json
from datetime import datetime
from decimal import Decimal

from server.geofence_live_db import build_live_state


def _fence():
    return {
        'id': 7,
        'public_id': 'fence-7',
        'nome': 'Garagem',
        'descricao': None,
        'regra': 'forbidden',
        'status': 'active',
        'owner_ref': None,
        'criado_por': 'test',
        'atualizado_por': 'test',
        'version': 1,
        'criado_em': datetime(2026, 11, 9, 8, 0),
        'atualizado_em': datetime(2026, 11, 9, 8, 0),
        'geometry_version_id': 9,
        'geometry_version': 1,
        'geometry_type': 'circle',
        'radius_meters': Decimal('300'),
        'geometry_hash': 'hash',
        'change_reason': 'teste',
        'geometry_created_by': 'test',
        'valid_from': datetime(2026, 11, 9, 8, 0),
        'valid_to': None,
        'geometry_created_at': datetime(2026, 11, 9, 8, 0),
        'geometry_geojson': json.dumps({
            'type': 'Point', 'coordinates': [-46.6333, -23.5505],
        }),
        'active_assignments': 1,
    }


def _assignment(**overrides):
    return {
        'assignment_id': 11,
        'geofence_id': 7,
        'target_type': 'vehicle',
        'assigned_vehicle_id': 21,
        'assigned_driver_id': None,
        'group_id': None,
        'timezone_name': 'America/Sao_Paulo',
        'effective_from': None,
        'effective_to': None,
        'dwell_threshold_seconds': 120,
        'hysteresis_meters': Decimal('30'),
        'target_label': 'ABC1D23',
        'subject_type': 'vehicle',
        'state_vehicle_id': 21,
        'state_driver_id': None,
        'stable_state': 'inside',
        'pending_state': None,
        'pending_samples': 0,
        'last_signed_distance_m': Decimal('42.5'),
        'last_latitude': Decimal('-23.5505000'),
        'last_longitude': Decimal('-46.6333000'),
        'last_accuracy_m': Decimal('5'),
        'last_source': 'tracker',
        'last_observed_at': datetime(2026, 11, 9, 10, 0),
        'last_transition_at': datetime(2026, 11, 9, 9, 59),
        'violation_started_at': datetime(2026, 11, 9, 9, 59),
        'dwell_notified_at': None,
        'violation_episode_id': 'episode-7',
        'subject_label': 'ABC1D23',
        **overrides,
    }


def test_builds_live_violation_with_schedule_position_and_episode():
    schedules = {11: [{
        'day_of_week': 0,
        'start_time': '08:00:00',
        'end_time': '18:00:00',
        'crosses_midnight': False,
    }]}

    result = build_live_state(
        [_fence()], [_assignment()], schedules, datetime(2026, 11, 9, 10, 1),
    )

    target = result[0]['targets'][0]
    assert target['stable_state'] == 'inside'
    assert target['schedule_active'] is True
    assert target['is_violation'] is True
    assert target['active_episode'] is True
    assert target['last_source'] == 'tracker'
    assert target['last_position'] == {
        'latitude': -23.5505, 'longitude': -46.6333,
        'accuracy_m': Decimal('5'), 'signed_distance_m': Decimal('42.5'),
    }
    assert result[0]['live_summary'] == {
        'targets': 1, 'inside': 1, 'outside': 0, 'unknown': 0,
        'violations': 1, 'active_episodes': 1,
    }


def test_schedule_closed_suppresses_operational_violation_without_hiding_state():
    schedules = {11: [{
        'day_of_week': 0,
        'start_time': '08:00:00',
        'end_time': '09:00:00',
        'crosses_midnight': False,
    }]}

    target = build_live_state(
        [_fence()], [_assignment()], schedules, datetime(2026, 11, 9, 10, 1),
    )[0]['targets'][0]

    assert target['stable_state'] == 'inside'
    assert target['schedule_active'] is False
    assert target['is_violation'] is False
    assert target['active_episode'] is False


def test_assignment_without_observation_is_explicitly_unknown():
    target = build_live_state(
        [_fence()], [_assignment(
            subject_type=None, state_vehicle_id=None, stable_state=None,
            last_latitude=None, last_longitude=None, violation_episode_id=None,
        )], {}, datetime(2026, 11, 9, 10, 1),
    )[0]['targets'][0]

    assert target['stable_state'] == 'unknown'
    assert target['last_position'] is None
    assert target['active_episode'] is False


def test_inactive_fence_suppresses_policy_without_hiding_schedule_or_state():
    fence = _fence()
    fence['status'] = 'inactive'

    target = build_live_state(
        [fence], [_assignment()], {}, datetime(2026, 11, 9, 10, 1),
    )[0]['targets'][0]

    assert target['stable_state'] == 'inside'
    assert target['schedule_active'] is True
    assert target['policy_active'] is False
    assert target['is_violation'] is False
    assert target['active_episode'] is False
