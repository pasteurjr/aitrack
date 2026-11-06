"""Política determinística de SLA dos incidentes operacionais."""

from datetime import datetime, timedelta
from typing import Dict, Optional


SLA_SECONDS = {
    'critical': 5 * 60,
    'high': 15 * 60,
    'medium': 60 * 60,
    'low': 4 * 60 * 60,
}


def deadline_for(severity: str, started_at: Optional[datetime] = None) -> datetime:
    if severity not in SLA_SECONDS:
        raise ValueError('Severidade sem política de SLA')
    return (started_at or datetime.now()) + timedelta(seconds=SLA_SECONDS[severity])


def enrich_sla(incident: Dict, now: Optional[datetime] = None) -> Dict:
    """Acrescenta estado/tempo do SLA sem alterar os campos persistidos."""
    now = now or datetime.now()
    result = dict(incident)
    due_at = incident.get('sla_due_at')
    if incident.get('status') in {'resolved', 'closed'}:
        result.update(sla_status='completed', sla_seconds_remaining=None, sla_progress_percent=100)
        return result
    if not isinstance(due_at, datetime):
        result.update(sla_status='not_set', sla_seconds_remaining=None, sla_progress_percent=None)
        return result

    remaining = int((due_at - now).total_seconds())
    started_at = incident.get('created_at') or incident.get('opened_at')
    total = int((due_at - started_at).total_seconds()) if isinstance(started_at, datetime) else 0
    consumed = max(0, total - remaining)
    progress = min(100, round(consumed / total * 100)) if total > 0 else None
    risk_window = max(5 * 60, int(total * 0.25)) if total > 0 else 5 * 60
    status = 'breached' if remaining <= 0 else ('at_risk' if remaining <= risk_window else 'on_track')
    result.update(
        sla_status=status,
        sla_seconds_remaining=remaining,
        sla_progress_percent=progress,
    )
    return result
