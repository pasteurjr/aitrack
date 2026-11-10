from datetime import datetime

from server.geofence_incident_worker import _payload


def test_builds_complete_retry_payload_from_persisted_event():
    observed_at = datetime(2026, 11, 10, 12, 0)
    row = {
        'id': 1,
        'public_id': 'event-1',
        'context_vehicle_id': 2,
        'driver_id': 3,
        'assignment_id': 4,
        'geofence_id': 5,
        'geometry_version_id': 6,
        'source_code': 'dirijabem',
        'event_type': 'geofence_dwell',
        'crossing_direction': None,
        'rule_applied': 'forbidden',
        'subject_type': 'driver',
        'latitude': -23.55,
        'longitude': -46.63,
        'observed_at': observed_at,
        'violation_episode_id': 'episode-1',
    }

    assert _payload(row) == {
        'geofence_event_id': 1,
        'public_id': 'event-1',
        'vehicle_id': 2,
        'driver_id': 3,
        'assignment_id': 4,
        'geofence_id': 5,
        'geometry_version_id': 6,
        'source': 'dirijabem',
        'event_type': 'geofence_dwell',
        'crossing_direction': None,
        'rule_applied': 'forbidden',
        'subject_type': 'driver',
        'latitude': -23.55,
        'longitude': -46.63,
        'observed_at': observed_at,
        'violation_episode_id': 'episode-1',
    }
