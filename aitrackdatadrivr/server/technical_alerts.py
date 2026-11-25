"""Avaliador interno; nunca dispara canal externo automaticamente."""

from .health_service import sanitize_reason
from .monitor_db import get_connection


def alert_plan(component):
    status = component.get('status')
    if status not in {'degraded', 'outage'}:
        return {'action': 'recover'}
    severity = 'critical' if status == 'outage' and component.get('critical') else (
        'high' if status == 'outage' else 'warning'
    )
    return {
        'action': 'open', 'severity': severity,
        'alert_type': 'component_unavailable' if status == 'outage' else 'component_degraded',
        'summary': sanitize_reason(
            component.get('reason_sanitized') or f'{component["component_key"]}: {status}'
        ),
    }


def evaluate_health_alerts(connection=None):
    owns = connection is None; conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True); changes = []
    try:
        if owns: conn.start_transaction()
        cursor.execute('SELECT * FROM monitoramento.health_components FOR UPDATE')
        for component in cursor.fetchall():
            key = f'health:{component["component_key"]}'
            plan = alert_plan(component)
            cursor.execute('SELECT state FROM monitoramento.technical_alerts WHERE alert_key=%s FOR UPDATE', (key,))
            existing = cursor.fetchone()
            if plan['action'] == 'open':
                cursor.execute("""INSERT INTO monitoramento.technical_alerts(
                  alert_key,component_key,alert_type,severity,state,reason_code,summary)
                  VALUES(%s,%s,%s,%s,'active',%s,%s)
                  ON DUPLICATE KEY UPDATE alert_type=VALUES(alert_type),severity=VALUES(severity),
                    state='active',reason_code=VALUES(reason_code),summary=VALUES(summary),
                    last_observed_at=CURRENT_TIMESTAMP(6),recovered_at=NULL,
                    occurrence_count=occurrence_count+1""",
                  (key, component['component_key'], plan['alert_type'], plan['severity'],
                   component.get('reason_code'), plan['summary']))
                transition = 'opened' if not existing or existing['state'] == 'recovered' else 'observed'
                cursor.execute("""INSERT INTO monitoramento.technical_alert_history(
                  alert_key,transition,reason_code) VALUES(%s,%s,%s)""",
                  (key, transition, component.get('reason_code')))
                changes.append({'alert_key': key, 'transition': transition})
            elif existing and existing['state'] == 'active':
                cursor.execute("""UPDATE monitoramento.technical_alerts SET state='recovered',
                  recovered_at=CURRENT_TIMESTAMP(6),last_observed_at=CURRENT_TIMESTAMP(6)
                  WHERE alert_key=%s""", (key,))
                cursor.execute("""INSERT INTO monitoramento.technical_alert_history(
                  alert_key,transition) VALUES(%s,'recovered')""", (key,))
                changes.append({'alert_key': key, 'transition': 'recovered'})
        if owns: conn.commit()
        return changes
    except Exception:
        if owns: conn.rollback()
        raise
    finally:
        cursor.close()
        if owns: conn.close()
