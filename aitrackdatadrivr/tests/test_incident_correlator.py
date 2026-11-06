from datetime import datetime

import pytest

from server.incident_correlator import correlate_episode


class FakeCursor:
    def __init__(
        self,
        vehicle=None,
        incident_created=True,
        evidence_added=True,
        incident_source='tracker',
    ):
        self.vehicle = vehicle if vehicle is not None else {
            'id': 12, 'device_id': 'SIM-1', 'codusu': 614,
        }
        self.incident_created = incident_created
        self.evidence_added = evidence_added
        self.incident_source = incident_source
        self.statements = []
        self.rowcount = 0
        self._fetchone = None
        self._fetchall = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        normalized = ' '.join(sql.split())
        self._fetchone = None
        self._fetchall = []
        if 'FROM tracker.veiculo_unificado' in normalized:
            self._fetchall = [] if self.vehicle is False else [self.vehicle]
        elif 'INSERT INTO tracker.incidents' in normalized:
            self.rowcount = 1 if self.incident_created else 0
        elif 'SELECT id, primary_source FROM tracker.incidents' in normalized:
            self._fetchone = {'id': 44, 'primary_source': self.incident_source}
        elif 'INSERT INTO tracker.incident_timeline' in normalized:
            self.rowcount = 1 if self.evidence_added else 0
        elif 'UPDATE tracker.incidents' in normalized:
            self.rowcount = 1

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return self._fetchall


def tracker_event(**overrides):
    return {
        'source': 'tracker',
        'source_record_id': 900,
        'device_id': 'SIM-1',
        'type': 'speeding',
        'severity': 'high',
        'timestamp': '2026-11-06T15:00:00Z',
        'lat': -23.55,
        'lon': -46.63,
        'speed': 91,
        'episode_id': 'episode-shared',
        **overrides,
    }


def test_creates_incident_and_auditable_tracker_evidence():
    cursor = FakeCursor()

    result = correlate_episode(cursor, tracker_event(), tracker_event_id=900, score_after=82.5)

    assert result == {
        'status': 'correlated',
        'incident_id': 44,
        'incident_created': True,
        'evidence_added': True,
        'correlation_key': 'behavior:12:episode-shared',
    }
    incident_insert = next(item for item in cursor.statements if 'INSERT INTO tracker.incidents' in item[0])
    assert incident_insert[1][1] == 12
    assert incident_insert[1][7] == 17.5
    timeline_insert = next(
        item for item in cursor.statements if 'INSERT INTO tracker.incident_timeline' in item[0]
    )
    assert timeline_insert[1][6] == 900
    assert timeline_insert[1][-1] == datetime(2026, 11, 6, 15, 0)


def test_replay_does_not_increment_incident_event_count():
    cursor = FakeCursor(incident_created=False, evidence_added=False)

    result = correlate_episode(cursor, tracker_event(), tracker_event_id=900)

    assert result['incident_created'] is False
    assert result['evidence_added'] is False
    assert not any('UPDATE tracker.incidents' in sql for sql, _params in cursor.statements)


def test_tracker_and_dirijabem_share_source_independent_correlation_key():
    tracker_cursor = FakeCursor()
    dirijabem_cursor = FakeCursor(incident_created=False, incident_source='tracker')

    tracker = correlate_episode(
        tracker_cursor,
        tracker_event(correlation_group='trip-risk-42'),
        tracker_event_id=900,
    )
    dirijabem = correlate_episode(dirijabem_cursor, {
        'source': 'dirijabem',
        'source_record_id': 'trip-77',
        'codusu': 614,
        'type': 'speeding',
        'severity': 'critical',
        'timestamp': '2026-11-06T15:00:03',
        'episode_id': 'dirijabem-episode-9',
        'correlation_group': 'trip-risk-42',
    })

    assert tracker['correlation_key'] == dirijabem['correlation_key']
    update = next(item for item in dirijabem_cursor.statements if 'UPDATE tracker.incidents' in item[0])
    assert update[1][0] == 'fused'
    assert 'version = version + 1' in update[0]
    timeline = next(
        item for item in dirijabem_cursor.statements if 'INSERT INTO tracker.incident_timeline' in item[0]
    )
    assert timeline[1][6] is None


def test_missing_unified_identity_is_ignored_without_partial_incident():
    cursor = FakeCursor(vehicle=False)

    result = correlate_episode(cursor, tracker_event())

    assert result == {'status': 'ignored', 'reason': 'vehicle_identity_not_found'}
    assert not any('INSERT INTO tracker.incidents' in sql for sql, _params in cursor.statements)


def test_legacy_event_without_episode_is_ignored_before_database_access():
    cursor = FakeCursor()

    result = correlate_episode(cursor, tracker_event(episode_id=None))

    assert result == {'status': 'ignored', 'reason': 'missing_episode_id'}
    assert cursor.statements == []


@pytest.mark.parametrize(
    'event, message',
    [
        ({'episode_id': 'x', 'source': 'unknown'}, 'source'),
        ({'episode_id': 'x', 'source': 'tracker', 'device_id': 'SIM-1'}, 'type'),
        ({
            'episode_id': 'x', 'source': 'dirijabem', 'codusu': 0,
            'type': 'speeding', 'severity': 'high', 'timestamp': '2026-11-06T15:00:00',
        }, 'codusu'),
    ],
)
def test_rejects_invalid_episode_contract(event, message):
    with pytest.raises(ValueError, match=message):
        correlate_episode(FakeCursor(), event)
