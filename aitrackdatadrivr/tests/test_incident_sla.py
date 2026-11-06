from datetime import datetime, timedelta

import pytest

from server.incident_sla import SLA_SECONDS, deadline_for, enrich_sla


NOW = datetime(2026, 11, 6, 12, 0)


@pytest.mark.parametrize(
    ('severity', 'seconds'),
    [('critical', 300), ('high', 900), ('medium', 3600), ('low', 14400)],
)
def test_deadline_policy_by_severity(severity, seconds):
    assert SLA_SECONDS[severity] == seconds
    assert deadline_for(severity, NOW) == NOW + timedelta(seconds=seconds)


def test_sla_is_on_track_before_risk_window():
    incident = {
        'status': 'new', 'created_at': NOW,
        'sla_due_at': NOW + timedelta(minutes=60),
    }

    result = enrich_sla(incident, now=NOW + timedelta(minutes=20))

    assert result['sla_status'] == 'on_track'
    assert result['sla_seconds_remaining'] == 2400
    assert result['sla_progress_percent'] == 33


def test_sla_enters_risk_window_at_last_quarter():
    incident = {
        'status': 'triage', 'created_at': NOW,
        'sla_due_at': NOW + timedelta(minutes=60),
    }

    result = enrich_sla(incident, now=NOW + timedelta(minutes=46))

    assert result['sla_status'] == 'at_risk'
    assert result['sla_seconds_remaining'] == 14 * 60


def test_sla_is_breached_at_deadline_and_keeps_negative_delay():
    incident = {
        'status': 'in_progress', 'created_at': NOW,
        'sla_due_at': NOW + timedelta(minutes=5),
    }

    result = enrich_sla(incident, now=NOW + timedelta(minutes=7))

    assert result['sla_status'] == 'breached'
    assert result['sla_seconds_remaining'] == -120
    assert result['sla_progress_percent'] == 100


@pytest.mark.parametrize('status', ['resolved', 'closed'])
def test_resolved_incident_has_completed_sla(status):
    result = enrich_sla({
        'status': status, 'created_at': NOW,
        'sla_due_at': NOW - timedelta(minutes=1),
    }, now=NOW)

    assert result['sla_status'] == 'completed'
    assert result['sla_seconds_remaining'] is None


def test_missing_deadline_is_explicit_not_set():
    result = enrich_sla({'status': 'new', 'sla_due_at': None}, now=NOW)

    assert result['sla_status'] == 'not_set'
    assert result['sla_progress_percent'] is None
