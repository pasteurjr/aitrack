from datetime import datetime, timedelta, timezone

from server import behavioral_engine as engine


def position(timestamp, speed=0, heading=0):
    return {
        "lat": -23.55,
        "lon": -46.63,
        "speed": speed,
        "heading": heading,
        "timestamp": timestamp,
    }


def history(*positions):
    from collections import deque

    return deque(positions, maxlen=engine.MAX_HISTORY_SIZE)


def test_acceleration_uses_real_elapsed_time():
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    events = engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=2), speed=20),
        history(
            position(start, speed=0),
            position(start + timedelta(seconds=0.5), speed=0),
            position(start + timedelta(seconds=1), speed=0),
        ),
    )

    acceleration = next(event for event in events if event["type"] == "harsh_accel")
    assert acceleration["elapsed_seconds"] == 2.0
    assert acceleration["acceleration_ms2"] == 2.78


def test_same_speed_delta_over_longer_interval_is_not_harsh():
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    events = engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=10), speed=20),
        history(
            position(start, speed=0),
            position(start + timedelta(seconds=1), speed=0),
            position(start + timedelta(seconds=2), speed=0),
        ),
    )

    assert not any(event["type"] == "harsh_accel" for event in events)


def test_out_of_order_timestamps_do_not_create_temporal_event():
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    events = engine.detect_events(
        "SIM-1",
        position(start - timedelta(seconds=1), speed=0),
        history(
            position(start, speed=50),
            position(start + timedelta(seconds=1), speed=50),
            position(start + timedelta(seconds=2), speed=50),
        ),
    )

    assert not any(event["type"] in {"harsh_accel", "harsh_brake"} for event in events)


def test_heading_wrap_around_uses_shortest_angle():
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    events = engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=4), speed=40, heading=1),
        history(
            position(start + timedelta(seconds=3), speed=40, heading=350),
            position(start + timedelta(seconds=3.25), speed=40, heading=350),
            position(start + timedelta(seconds=3.5), speed=40, heading=350),
            position(start + timedelta(seconds=3.75), speed=40, heading=350),
            position(start + timedelta(seconds=4), speed=40, heading=1),
        ),
    )

    turn = next(event for event in events if event["type"] == "sharp_turn")
    assert turn["heading_change"] == 11
    assert turn["turn_rate_deg_per_sec"] == 11.0


def test_score_uses_only_events_from_last_hour():
    engine.reset_all()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    engine.vehicle_scores["SIM-1"] = engine.INITIAL_SCORE
    engine.vehicle_events.extend([
        {
            "device_id": "SIM-1",
            "type": "harsh_brake",
            "severity": "high",
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
        },
        {
            "device_id": "SIM-1",
            "type": "speeding",
            "severity": "high",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
        },
    ])

    assert engine.calculate_vehicle_score("SIM-1", now=now) == 95.5


def test_score_recovers_after_event_expires():
    engine.reset_all()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    engine.vehicle_scores["SIM-1"] = engine.INITIAL_SCORE
    engine.vehicle_events.append({
        "device_id": "SIM-1",
        "type": "harsh_brake",
        "severity": "medium",
        "timestamp": (now - timedelta(minutes=30)).isoformat(),
    })

    assert engine.calculate_vehicle_score("SIM-1", now=now) == 97.0
    assert engine.calculate_vehicle_score(
        "SIM-1", now=now + timedelta(hours=2)
    ) == 100.0


def test_speeding_emits_one_event_per_episode_and_rearms_below_hysteresis():
    start = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    state = {}

    first = engine.detect_events(
        "SIM-1",
        position(start, speed=81),
        history(position(start - timedelta(seconds=1), speed=79)),
        state,
    )
    continuous = engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=1), speed=110),
        history(position(start, speed=81)),
        state,
    )
    engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=2), speed=74),
        history(position(start + timedelta(seconds=1), speed=110)),
        state,
    )
    second = engine.detect_events(
        "SIM-1",
        position(start + timedelta(seconds=3), speed=85),
        history(position(start + timedelta(seconds=2), speed=74)),
        state,
    )

    first_speeding = [event for event in first if event['type'] == 'speeding']
    second_speeding = [event for event in second if event['type'] == 'speeding']
    assert len(first_speeding) == 1
    assert not any(event['type'] == 'speeding' for event in continuous)
    assert len(second_speeding) == 1
    assert first_speeding[0]['episode_state'] == 'started'
    assert first_speeding[0]['episode_id'] != second_speeding[0]['episode_id']


def test_speeding_does_not_rearm_at_release_boundary():
    start = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    state = {}
    engine._detect_speeding_episode("SIM-1", position(start, speed=90), state)

    assert engine._detect_speeding_episode(
        "SIM-1", position(start + timedelta(seconds=1), speed=75), state
    ) is None
    assert engine._detect_speeding_episode(
        "SIM-1", position(start + timedelta(seconds=2), speed=90), state
    ) is None


def test_transient_detector_suppresses_continuous_condition_and_fast_retrigger():
    start = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    state = {}

    first = engine._detector_episode_gate(
        'SIM-1', 'harsh_brake', start, True, False, state
    )
    continuous = engine._detector_episode_gate(
        'SIM-1', 'harsh_brake', start + timedelta(seconds=1), True, False, state
    )
    engine._detector_episode_gate(
        'SIM-1', 'harsh_brake', start + timedelta(seconds=2), False, True, state
    )
    fast_retrigger = engine._detector_episode_gate(
        'SIM-1', 'harsh_brake', start + timedelta(seconds=3), True, False, state
    )

    assert first is not None
    assert continuous is None
    assert fast_retrigger is None


def test_transient_detector_rearms_after_release_and_cooldown():
    start = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    state = {}
    first = engine._detector_episode_gate(
        'SIM-1', 'sharp_turn', start, True, False, state
    )
    engine._detector_episode_gate(
        'SIM-1', 'sharp_turn', start + timedelta(seconds=1), False, True, state
    )
    second = engine._detector_episode_gate(
        'SIM-1',
        'sharp_turn',
        start + timedelta(seconds=engine.DETECTOR_COOLDOWN_SECONDS + 1),
        True,
        False,
        state,
    )

    assert first is not None
    assert second is not None
    assert first != second


def test_all_transient_events_receive_episode_metadata():
    start = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    scenarios = {
        'harsh_accel': history(
            position(start, speed=0),
            position(start + timedelta(seconds=1), speed=0),
            position(start + timedelta(seconds=2), speed=20),
        ),
        'harsh_brake': history(
            position(start, speed=50),
            position(start + timedelta(seconds=1), speed=50),
            position(start + timedelta(seconds=2), speed=20),
        ),
        'sharp_turn': history(
            position(start, speed=40, heading=0),
            position(start + timedelta(seconds=0.25), speed=40, heading=0),
            position(start + timedelta(seconds=0.5), speed=40, heading=0),
            position(start + timedelta(seconds=0.75), speed=40, heading=0),
            position(start + timedelta(seconds=1), speed=40, heading=90),
        ),
    }

    for event_type, sample_history in scenarios.items():
        current = sample_history[-1]
        event = next(
            item for item in engine.detect_events('SIM-1', current, sample_history, {})
            if item['type'] == event_type
        )
        assert event['episode_id']
        assert event['episode_state'] == 'started'


def test_event_and_score_are_persisted_in_the_same_transaction(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.statements = []

        def execute(self, sql, params=None):
            self.statements.append((sql, params))

        def fetchone(self):
            return {'id': 7}

        def close(self):
            pass

    class FakeConnection:
        def __init__(self):
            self.cursor_instance = FakeCursor()
            self.commits = 0
            self.rollbacks = 0

        def cursor(self, dictionary=False):
            return self.cursor_instance

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            pass

    connection = FakeConnection()
    monkeypatch.setattr(engine.mysql.connector, 'connect', lambda **_kwargs: connection)
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)

    engine.save_event_to_db({
        'device_id': 'SIM-1',
        'type': 'speeding',
        'lat': -23.55,
        'lon': -46.63,
        'timestamp': now.isoformat(),
        'severity': 'high',
        'speed': 90,
        'episode_id': 'episode-1',
    }, veicod=1, score_after=98.5, events_in_window=1)

    statements = [sql for sql, _params in connection.cursor_instance.statements]
    assert any('INSERT INTO eventos' in sql for sql in statements)
    assert any('INSERT INTO tracker.behavioral_scores' in sql for sql in statements)
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_persisted_state_restores_events_score_and_detector_without_duplicates():
    engine.reset_all()
    now = datetime.now(timezone.utc)
    score_rows = [{'device_id': 'SIM-1', 'score': 88.0}]
    event_rows = [{
        'id': 321,
        'device_id': 'SIM-1',
        'type': 'harsh_brake',
        'timestamp': now - timedelta(minutes=1),
        'lat': -23.55,
        'lon': -46.63,
        'speed': 20,
        'severity': 'high',
        'dados_adicionais': '{"episode_id": "episode-321", "episode_state": "started"}',
    }]

    first = engine._merge_persisted_state(score_rows, event_rows)
    second = engine._merge_persisted_state(score_rows, event_rows)

    assert first == {'scores': 1, 'events': 1}
    assert second == {'scores': 1, 'events': 0}
    assert len(engine.vehicle_events) == 1
    assert engine.vehicle_events[0]['episode_id'] == 'episode-321'
    assert engine.vehicle_detector_state['SIM-1']['harsh_brake']['active'] is True
    assert engine.vehicle_scores['SIM-1'] == 95.5
