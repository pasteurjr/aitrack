"""Cálculo puro de SLA, tempos operacionais e grau de automação."""

from datetime import datetime, timedelta
import math
from statistics import median


OPEN_STATUSES = {'new', 'triage', 'in_progress', 'waiting_response', 'escalated'}


def duration_seconds(start, end):
    if not start or not end or end < start:
        return None
    return (end - start).total_seconds()


def distribution(values, total):
    valid = sorted(value for value in values if value is not None)
    if not valid:
        return {'valid_count': 0, 'excluded_count': total, 'median_seconds': None, 'p95_seconds': None}
    p95_index = max(0, math.ceil(len(valid) * 0.95) - 1)
    return {
        'valid_count': len(valid),
        'excluded_count': total - len(valid),
        'median_seconds': round(median(valid), 2),
        'p95_seconds': round(valid[p95_index], 2),
    }


def calculate_operations_metrics(incidents, action_summary, as_of=None):
    now = as_of or datetime.utcnow()
    total = len(incidents)
    detection = [duration_seconds(row.get('position_observed_at'), row.get('opened_at')) for row in incidents]
    triage = [duration_seconds(row.get('opened_at'), row.get('triaged_at') or row.get('acknowledged_at')) for row in incidents]
    resolution = [duration_seconds(row.get('opened_at'), row.get('resolved_at')) for row in incidents]
    sla = {'within': 0, 'at_risk': 0, 'breached': 0, 'excluded': 0}
    for row in incidents:
        due = row.get('sla_due_at')
        if not due:
            sla['excluded'] += 1
        elif row.get('resolved_at'):
            sla['within' if row['resolved_at'] <= due else 'breached'] += 1
        elif row.get('status') in OPEN_STATUSES:
            if now > due:
                sla['breached'] += 1
            elif due - now <= timedelta(minutes=30):
                sla['at_risk'] += 1
            else:
                sla['within'] += 1
        else:
            sla['excluded'] += 1
    automated_incidents = int(action_summary.get('automated_incidents') or 0)
    human_incidents = sum(1 for row in incidents if row.get('assigned_type') == 'human' or row.get('human_owned'))
    return {
        'incident_count': total,
        'detection': distribution(detection, total),
        'triage': distribution(triage, total),
        'resolution': distribution(resolution, total),
        'sla': {**sla, 'valid_count': total - sla['excluded']},
        'automation': {
            'automated_incidents': automated_incidents,
            'denominator': total,
            'rate': automated_incidents / total if total else None,
            'simulated_actions': int(action_summary.get('simulated_actions') or 0),
            'externally_sent_actions': int(action_summary.get('externally_sent_actions') or 0),
        },
        'human_intervention': {
            'incidents': human_incidents,
            'denominator': total,
            'rate': human_incidents / total if total else None,
        },
        'action_failures': {
            'transient_failed': int(action_summary.get('transient_failed') or 0),
            'dead_letter': int(action_summary.get('dead_letter') or 0),
        },
    }
