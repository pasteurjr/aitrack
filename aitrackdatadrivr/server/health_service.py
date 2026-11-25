"""Snapshot sanitizado de prontidão, integrações, workers e filas."""

from datetime import datetime, timezone
import re

from .monitor_db import get_connection


VALID_STATUS = {'unknown', 'healthy', 'degraded', 'outage'}
SECRET_PATTERNS = (
    re.compile(r'(?i)bearer\s+[^\s,;]+'),
    re.compile(r'(?i)(https?://[^:/\s]+:)[^@/\s]+@'),
    re.compile(r'(?i)(["\']?(?:password|passwd|token|secret|api[_-]?key|authorization)["\']?\s*[:=]\s*["\']?)[^"\'\s,;}]+'),
)


def sanitize_reason(value):
    if not value:
        return None
    safe = str(value)
    safe = SECRET_PATTERNS[0].sub('Bearer [REDACTED]', safe)
    safe = SECRET_PATTERNS[1].sub(r'\1[REDACTED]@', safe)
    safe = SECRET_PATTERNS[2].sub(r'\1[REDACTED]', safe)
    return safe[:500]


def status_from_age(age_seconds, degraded_after, outage_after):
    if age_seconds is None:
        return 'unknown'
    if age_seconds >= outage_after:
        return 'outage'
    if age_seconds >= degraded_after:
        return 'degraded'
    return 'healthy'


def update_component(component_key, status, *, reason_code=None, reason=None,
                     heartbeat_at=None, success=False, failure=False,
                     latency_ms=None, lag_seconds=None, queue_depth=None,
                     oldest_item_seconds=None, connection=None):
    if status not in VALID_STATUS:
        raise ValueError('status de saúde inválido')
    owns = connection is None; conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns: conn.start_transaction()
        cursor.execute(
            'SELECT status FROM monitoramento.health_components '
            'WHERE component_key=%s FOR UPDATE', (component_key,),
        )
        previous = cursor.fetchone()
        if not previous:
            raise LookupError('componente de saúde desconhecido')
        safe_reason = sanitize_reason(reason)
        cursor.execute("""
          UPDATE monitoramento.health_components SET status=%s,
            heartbeat_at=COALESCE(%s,heartbeat_at),
            last_success_at=CASE WHEN %s THEN CURRENT_TIMESTAMP(6) ELSE last_success_at END,
            last_failure_at=CASE WHEN %s THEN CURRENT_TIMESTAMP(6) ELSE last_failure_at END,
            latency_ms=%s,lag_seconds=%s,queue_depth=%s,oldest_item_seconds=%s,
            reason_code=%s,reason_sanitized=%s WHERE component_key=%s
        """, (status, heartbeat_at, success, failure, latency_ms, lag_seconds,
              queue_depth, oldest_item_seconds, reason_code, safe_reason, component_key))
        if previous['status'] != status:
            cursor.execute("""
              INSERT INTO monitoramento.health_transitions(
                component_key,from_status,to_status,reason_code,reason_sanitized)
              VALUES(%s,%s,%s,%s,%s)
            """, (component_key, previous['status'], status, reason_code, safe_reason))
        if owns: conn.commit()
    except Exception:
        if owns: conn.rollback()
        raise
    finally:
        cursor.close()
        if owns: conn.close()


def readiness():
    try:
        conn = get_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT 1 ok')
        database_ok = cursor.fetchone()['ok'] == 1
        cursor.execute("""SELECT COUNT(*) total FROM monitoramento.health_components
          WHERE critical=TRUE AND component_key NOT IN
            ('database','tracker_ingestion','dirijabem_ingestion')
            AND status IN ('unknown','outage')""")
        blocker_count = int(cursor.fetchone()['total'])
        cursor.execute("""SELECT COUNT(*) total FROM monitoramento.integration_health
          WHERE source_code IN ('tracker','dirijabem') AND status IN ('unknown','outage')""")
        blocker_count += int(cursor.fetchone()['total'])
        return {'status': 'ready' if database_ok and blocker_count == 0 else 'not_ready',
                'database': database_ok, 'blocker_count': blocker_count}
    except Exception:
        return {'status': 'not_ready', 'database': False, 'blocker_count': 1}
    finally:
        try: cursor.close(); conn.close()
        except (NameError, AttributeError): pass


def integration_snapshot(history_limit=30):
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM monitoramento.health_components ORDER BY critical DESC,component_key')
        components = cursor.fetchall()
        cursor.execute("""SELECT source_code,status,last_success_at,last_failure_at,reason,updated_at
          FROM monitoramento.integration_health ORDER BY source_code""")
        source_health = {row['source_code']: row for row in cursor.fetchall()}
        for item in components:
            source_code = item['component_key'].removesuffix('_ingestion')
            source = source_health.get(source_code)
            if source:
                item['status'] = source['status']
                item['last_success_at'] = source['last_success_at']
                item['last_failure_at'] = source['last_failure_at']
                item['reason_sanitized'] = sanitize_reason(source['reason'])
        cursor.execute("""SELECT * FROM monitoramento.health_transitions
          ORDER BY occurred_at DESC,id DESC LIMIT %s""", (history_limit,))
        history = cursor.fetchall()
        cursor.execute("""SELECT alert_key,component_key,alert_type,severity,summary,
          opened_at,last_observed_at,occurrence_count
          FROM monitoramento.technical_alerts WHERE state='active'
          ORDER BY FIELD(severity,'critical','high','warning'),last_observed_at DESC""")
        active_alerts = cursor.fetchall()
        for collection in (components, history, active_alerts):
            for row in collection:
                for key, value in list(row.items()):
                    if isinstance(value, datetime): row[key] = value.isoformat()
                    elif isinstance(value, bool): row[key] = bool(value)
        states = [item['status'] for item in components]
        overall = ('outage' if 'outage' in states else
                   'degraded' if any(x in states for x in ('degraded','unknown')) else 'healthy')
        return {'schema_version': 'integration-health.v1',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'overall_status': overall, 'components': components,
                'history': history, 'active_alerts': active_alerts}
    finally:
        cursor.close(); conn.close()
