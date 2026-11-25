from pathlib import Path

import pytest

from server.report_service import combine_sources


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '059_create_analytics_reports.sql'


def analytics_fixture():
    return {
        'source_totals': {'tracker': 10, 'dirijabem': 2},
        'by_type': [
            {'source': 'tracker', 'event_type': 'speeding', 'total': 10},
            {'source': 'dirijabem', 'event_type': 'speeding', 'total': 2},
        ],
        'exposure': {
            'tracker': {'distance_km': 100, 'driving_seconds': 7200, 'coverage': 1, 'quality': 'complete'},
            'dirijabem': {'distance_km': 20, 'driving_seconds': 3600, 'coverage': 0.5, 'quality': 'partial'},
        },
    }


def test_unified_report_recalculates_weighted_rates_and_keeps_sources():
    result = combine_sources(analytics_fixture(), 'unified')
    assert result['event_count'] == 12
    assert result['distance_km'] == 120
    assert result['events_per_100_km'] == 10
    assert result['events_per_driving_hour'] == 4
    assert set(result['source_breakdown']) == {'tracker', 'dirijabem'}


def test_source_report_never_leaks_other_source():
    result = combine_sources(analytics_fixture(), 'tracker')
    assert result['sources'] == ['tracker']
    assert set(result['source_breakdown']) == {'tracker'}
    assert result['event_count'] == 10
    with pytest.raises(ValueError):
        combine_sources(analytics_fixture(), 'mock')


def test_report_schema_is_immutable_and_versioned():
    sql = MIGRATION.read_text().lower()
    for token in ('report_definitions', 'report_runs', 'request_hash', 'trg_report_run_update', 'source'):
        assert token in sql
