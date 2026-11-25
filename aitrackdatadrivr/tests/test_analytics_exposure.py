from datetime import datetime, timedelta
from pathlib import Path

from server.analytics_exposure import calculate_exposure, normalize_event_count


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '058_create_analytics_exposure_buckets.sql'


def point(at, longitude, speed=30):
    return {'observed_at': at, 'latitude': -23.55, 'longitude': longitude, 'speed_kmh': speed}


def test_exposure_calculates_distance_and_driving_time():
    start = datetime(2026, 11, 25)
    result = calculate_exposure([
        point(start, -46.63),
        point(start + timedelta(seconds=60), -46.629),
        point(start + timedelta(seconds=120), -46.628),
    ])
    assert 0.19 < result['distance_km'] < 0.22
    assert result['driving_seconds'] == 120
    assert result['coverage'] == 1
    assert result['quality'] == 'complete'


def test_exposure_discards_gap_and_impossible_jump():
    start = datetime(2026, 11, 25)
    result = calculate_exposure([
        point(start, -46.63),
        point(start + timedelta(seconds=600), -46.629),
        point(start + timedelta(seconds=601), -40),
    ])
    assert result['distance_km'] == 0
    assert result['discarded_segments'] == 2
    assert result['quality'] == 'partial'


def test_normalization_never_invents_rate_without_denominator():
    assert normalize_event_count(4, 20, 7200) == {
        'events_per_100_km': 20.0,
        'events_per_driving_hour': 2.0,
    }
    assert normalize_event_count(4, 0, 0) == {
        'events_per_100_km': None,
        'events_per_driving_hour': None,
    }


def test_migration_is_additive_and_uses_unified_database():
    sql = MIGRATION.read_text().lower()
    assert 'monitoramento.analytics_exposure_buckets' in sql
    assert 'monitoramento.analytics_materialization_offsets' in sql
    assert 'insert into tracker' not in sql and 'insert into dirijabem' not in sql
