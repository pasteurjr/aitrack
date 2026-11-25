"""Consultas temporais dos indicadores operacionais."""

from datetime import datetime

from .monitor_db import get_connection
from .operations_metrics import calculate_operations_metrics


ALLOWED_SOURCES = {'tracker', 'dirijabem', 'fused', 'system'}
ALLOWED_SEVERITIES = {'low', 'medium', 'high', 'critical'}


def get_operations_metrics(period, source=None, severity=None, incident_type=None, as_of=None, connection=None):
    if source and source not in ALLOWED_SOURCES:
        raise ValueError('source inválida')
    if severity and severity not in ALLOWED_SEVERITIES:
        raise ValueError('severity inválida')
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    clauses = ['i.opened_at >= %s', 'i.opened_at < %s']
    params = [period.start_utc, period.end_utc]
    for field, value in (('i.primary_source', source), ('i.severity', severity), ('i.incident_type', incident_type)):
        if value:
            clauses.append(f'{field}=%s')
            params.append(value)
    where = ' AND '.join(clauses)
    try:
        cursor.execute(
            f"""SELECT i.id,i.status,i.assigned_type,i.position_observed_at,i.opened_at,
                       i.triaged_at,i.acknowledged_at,i.sla_due_at,i.resolved_at,
                       (c.control_state='human_owned') human_owned
                  FROM monitoramento.incidents i
                  LEFT JOIN monitoramento.agent_incident_controls c ON c.incident_id=i.id
                 WHERE {where} ORDER BY i.opened_at,i.id LIMIT 10000""",
            tuple(params),
        )
        incidents = cursor.fetchall()
        cursor.execute(
            f"""SELECT
                  COUNT(DISTINCT CASE WHEN q.agent_run_id IS NOT NULL AND q.status IN ('sent','delivered','responded','simulated') THEN i.id END) automated_incidents,
                  SUM(q.status='simulated') simulated_actions,
                  SUM(q.status IN ('sent','delivered','responded')) externally_sent_actions,
                  SUM(q.status='failed') transient_failed,
                  SUM(q.status='dead') dead_letter
                FROM monitoramento.incidents i
                LEFT JOIN monitoramento.action_queue q ON q.incident_id=i.id
               WHERE {where}""",
            tuple(params),
        )
        action_summary = cursor.fetchone() or {}
    finally:
        cursor.close()
        if owns_connection:
            conn.close()
    metrics = calculate_operations_metrics(incidents, action_summary, as_of or datetime.utcnow())
    return {
        'schema_version': 'operations-metrics.v1',
        'period': period.public(),
        'filters': {'source': source, 'severity': severity, 'incident_type': incident_type},
        **metrics,
    }
