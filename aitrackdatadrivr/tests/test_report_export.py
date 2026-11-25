from datetime import datetime, timezone
from pathlib import Path

from server.report_export import next_schedule_run, safe_csv_cell, serialize_report


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '061_create_report_exports.sql'


def report_fixture(source='=tracker'):
    return {
        'public_id': 'report-1', 'formula_version': 'exposure-v1',
        'filters': {'from': '2026-11-24T00:00:00+00:00', 'to': '2026-11-25T00:00:00+00:00'},
        'summary': {
            'mode': 'tracker',
            'source_breakdown': {source: {'event_count': 2, 'distance_km': 10, 'driving_seconds': 3600, 'quality': 'complete'}},
        },
    }


def test_csv_escapes_formula_and_json_preserves_provenance():
    assert safe_csv_cell('=1+1') == "'=1+1"
    assert safe_csv_cell('+cmd') == "'+cmd"
    csv_bytes, rows = serialize_report(report_fixture(), 'csv')
    json_bytes, json_rows = serialize_report(report_fixture('tracker'), 'json')
    assert b"'=tracker" in csv_bytes and rows == 1
    assert b'"formula_version":"exposure-v1"' in json_bytes and json_rows == 1


def test_schedule_handles_daily_and_weekly_in_timezone():
    after = datetime(2026, 11, 25, 15, tzinfo=timezone.utc)
    daily = next_schedule_run('daily', '09:00', 'America/Sao_Paulo', after=after)
    weekly = next_schedule_run('weekly', '09:00', 'America/Sao_Paulo', weekday=2, after=after)
    assert daily > after.replace(tzinfo=None)
    assert weekly > after.replace(tzinfo=None)


def test_export_schema_is_internal_and_auditable():
    sql = MIGRATION.read_text().lower()
    for token in ('report_export_schedules', 'report_export_jobs', 'report_export_events', 'blocked_auth', 'internal_download', 'artifact_sha256'):
        assert token in sql
