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
