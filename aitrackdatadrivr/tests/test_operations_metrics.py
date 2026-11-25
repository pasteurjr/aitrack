from datetime import datetime, timedelta
from pathlib import Path

from server.operations_metrics import calculate_operations_metrics, distribution, duration_seconds


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '060_add_incident_analytics_index.sql'


def test_duration_and_distribution_exclude_invalid_values():
    now = datetime(2026, 11, 25)
    assert duration_seconds(now, now + timedelta(seconds=10)) == 10
    assert duration_seconds(now, now - timedelta(seconds=1)) is None
    assert distribution([1, 2, 3, None], 4) == {
        'valid_count': 3, 'excluded_count': 1, 'median_seconds': 2, 'p95_seconds': 3,
    }


def test_metrics_separate_sla_automation_human_and_failures():
    now = datetime(2026, 11, 25, 12)
    incidents = [
        {
            'status': 'resolved', 'assigned_type': 'agent', 'human_owned': False,
            'position_observed_at': now - timedelta(minutes=12),
            'opened_at': now - timedelta(minutes=10), 'triaged_at': now - timedelta(minutes=8),
            'resolved_at': now - timedelta(minutes=1), 'sla_due_at': now,
        },
        {
            'status': 'in_progress', 'assigned_type': 'human', 'human_owned': True,
            'position_observed_at': None, 'opened_at': now - timedelta(hours=2),
            'triaged_at': None, 'acknowledged_at': None, 'resolved_at': None,
            'sla_due_at': now - timedelta(minutes=1),
        },
        {
            'status': 'new', 'assigned_type': None, 'human_owned': False,
            'position_observed_at': now + timedelta(seconds=1), 'opened_at': now,
            'triaged_at': None, 'resolved_at': None, 'sla_due_at': None,
        },
    ]
    result = calculate_operations_metrics(incidents, {
        'automated_incidents': 1, 'simulated_actions': 2, 'externally_sent_actions': 1,
        'transient_failed': 3, 'dead_letter': 1,
    }, now)
    assert result['detection']['valid_count'] == 1
    assert result['sla'] == {'within': 1, 'at_risk': 0, 'breached': 1, 'excluded': 1, 'valid_count': 2}
    assert result['automation']['rate'] == 1 / 3
    assert result['human_intervention']['incidents'] == 1
    assert result['action_failures'] == {'transient_failed': 3, 'dead_letter': 1}


def test_empty_denominators_are_null_not_zero():
    result = calculate_operations_metrics([], {}, datetime(2026, 11, 25))
    assert result['automation']['rate'] is None
    assert result['human_intervention']['rate'] is None
    assert result['detection']['median_seconds'] is None


def test_period_index_starts_with_opened_at():
    sql = MIGRATION.read_text().lower()
    assert 'monitoramento.incidents(opened_at, id)' in sql
