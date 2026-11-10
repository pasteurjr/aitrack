from datetime import datetime

import pytest

from server.incident_correlator import correlate_geofence_event


class FakeCursor:
    def __init__(
        self, incident_created=True, evidence_added=True, source='tracker',
        incident_exists=True, link_rowcount=1, linked_incident_id=77,
    ):
        self.incident_created = incident_created
        self.evidence_added = evidence_added
        self.source = source
        self.incident_exists = incident_exists
        self.link_rowcount = link_rowcount
        self.linked_incident_id = linked_incident_id
        self.statements = []
        self.rowcount = 0
        self.lastrowid = 501
        self._fetchone = None

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        normalized = ' '.join(sql.split())
        self._fetchone = None
        if 'INSERT INTO monitoramento.incidents' in normalized:
            self.rowcount = 1 if self.incident_created else 0
        elif 'SELECT GET_LOCK' in normalized:
            self._fetchone = {'acquired': 1}
        elif 'SELECT RELEASE_LOCK' in normalized:
            self._fetchone = {'released': 1}
        elif 'SELECT id, primary_source FROM monitoramento.incidents' in normalized:
            self._fetchone = (
                {'id': 77, 'primary_source': self.source}
                if self.incident_exists else None
            )
        elif 'INSERT INTO monitoramento.incident_timeline' in normalized:
            self.rowcount = 1 if self.evidence_added else 0
        elif 'UPDATE monitoramento.incidents' in normalized:
            self.rowcount = 1
        elif 'UPDATE monitoramento.geofence_events' in normalized:
            self.rowcount = self.link_rowcount
        elif 'SELECT incident_id FROM monitoramento.geofence_events' in normalized:
            self._fetchone = {'incident_id': self.linked_incident_id}

    def fetchone(self):
        return self._fetchone


def geofence_event(**overrides):
    return {
        'geofence_event_id': 501,
        'public_id': '12345678-1234-5678-1234-567812345678',
        'vehicle_id': 12,
        'driver_id': 34,
        'assignment_id': 45,
        'geofence_id': 56,
        'geometry_version_id': 67,
        'source': 'tracker',
        'event_type': 'geofence_exit',
        'crossing_direction': 'inside_to_outside',
        'rule_applied': 'allowed',
        'subject_type': 'vehicle',
        'latitude': -23.55,
        'longitude': -46.63,
        'observed_at': '2026-11-10T15:00:00Z',
        'violation_episode_id': 'aaaaaaaa-bbbb-5ccc-8ddd-eeeeeeeeeeee',
        **overrides,
    }


def test_creates_incident_and_links_full_geofence_evidence():
    cursor = FakeCursor()

    result = correlate_geofence_event(cursor, geofence_event())

    assert result == {
        'status': 'correlated',
        'incident_id': 77,
        'incident_created': True,
        'evidence_added': True,
        'correlation_key': 'geofence:aaaaaaaa-bbbb-5ccc-8ddd-eeeeeeeeeeee',
        'violation': True,
    }
    incident_insert = next(
        item for item in cursor.statements
        if 'INSERT INTO monitoramento.incidents' in item[0]
    )
    assert incident_insert[1][1] == 12
    assert incident_insert[1][5] == 'critical'
    timeline_insert = next(
        item for item in cursor.statements
        if 'INSERT INTO monitoramento.incident_timeline' in item[0]
    )
    assert timeline_insert[1][7] == '12345678-1234-5678-1234-567812345678'
    assert timeline_insert[1][-1] == datetime(2026, 11, 10, 15, 0)
    assert any(
        'UPDATE monitoramento.geofence_events' in sql
        for sql, _params in cursor.statements
    )


def test_replay_does_not_increment_event_count():
    cursor = FakeCursor(incident_created=False, evidence_added=False)

    result = correlate_geofence_event(cursor, geofence_event())

    assert result['incident_created'] is False
    assert result['evidence_added'] is False
    assert not any(
        'UPDATE monitoramento.incidents' in sql
        for sql, _params in cursor.statements
    )


def test_recovery_uses_low_severity_and_same_episode_key():
    cursor = FakeCursor(incident_created=False)

    result = correlate_geofence_event(cursor, geofence_event(
        event_type='geofence_entry',
        crossing_direction='outside_to_inside',
    ))

    assert result['violation'] is False
    assert result['correlation_key'] == (
        'geofence:aaaaaaaa-bbbb-5ccc-8ddd-eeeeeeeeeeee'
    )
    incident_insert = next(
        item for item in cursor.statements
        if 'INSERT INTO monitoramento.incidents' in item[0]
    )
    assert incident_insert[1][5] == 'low'


def test_recovery_without_open_violation_does_not_create_false_incident():
    cursor = FakeCursor(incident_exists=False)

    result = correlate_geofence_event(cursor, geofence_event(
        event_type='geofence_entry',
        crossing_direction='outside_to_inside',
    ))

    assert result == {
        'status': 'ignored', 'reason': 'violation_incident_not_found',
    }
    assert not any(
        'INSERT INTO monitoramento.incidents' in sql
        for sql, _params in cursor.statements
    )


def test_rejects_event_already_linked_to_another_incident():
    cursor = FakeCursor(link_rowcount=0, linked_incident_id=88)

    with pytest.raises(RuntimeError, match='ligado a outro incidente'):
        correlate_geofence_event(cursor, geofence_event())


def test_driver_without_unified_vehicle_keeps_event_without_incident():
    cursor = FakeCursor()

    result = correlate_geofence_event(cursor, geofence_event(vehicle_id=None))

    assert result == {'status': 'ignored', 'reason': 'vehicle_identity_not_found'}
    assert cursor.statements == []


@pytest.mark.parametrize(
    ('field', 'value', 'message'),
    [
        ('source', 'unknown', 'source'),
        ('event_type', 'panic', 'event_type'),
        ('rule_applied', 'maybe', 'rule_applied'),
        ('vehicle_id', -1, 'vehicle_id'),
    ],
)
def test_rejects_invalid_geofence_contract(field, value, message):
    with pytest.raises(ValueError, match=message):
        correlate_geofence_event(FakeCursor(), geofence_event(**{field: value}))
