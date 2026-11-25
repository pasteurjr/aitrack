"""Geração rastreável de relatórios por origem e unificados."""

from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from .analytics_db import aggregate_behavior
from .analytics_exposure import FORMULA_VERSION, normalize_event_count
from .analytics_periods import parse_period
from .monitor_db import get_connection


REPORT_SOURCES = {
    'tracker': ('tracker',),
    'dirijabem': ('dirijabem',),
    'unified': ('tracker', 'dirijabem'),
}


def combine_sources(analytics, mode):
    if mode not in REPORT_SOURCES:
        raise ValueError('mode deve ser tracker, dirijabem ou unified')
    sources = REPORT_SOURCES[mode]
    distance = sum(analytics['exposure'][source]['distance_km'] for source in sources)
    seconds = sum(analytics['exposure'][source]['driving_seconds'] for source in sources)
    raw_events = sum(analytics['source_totals'].get(source, 0) for source in sources)
    by_event = {}
    for row in analytics['by_type']:
        if row['source'] in sources:
            by_event[row['event_type']] = by_event.get(row['event_type'], 0) + row['total']
    rows = [
        {'event_type': event_type, 'event_count': count, **normalize_event_count(count, distance, seconds)}
        for event_type, count in sorted(by_event.items())
    ]
    coverage_values = [analytics['exposure'][source]['coverage'] for source in sources]
    return {
        'mode': mode,
        'sources': list(sources),
        'event_count': raw_events,
        'distance_km': round(distance, 6),
        'driving_seconds': seconds,
        'coverage': sum(coverage_values) / len(coverage_values),
        **normalize_event_count(raw_events, distance, seconds),
        'rows': rows,
        'source_breakdown': {
            source: {
                'event_count': analytics['source_totals'].get(source, 0),
                **analytics['exposure'][source],
            }
            for source in sources
        },
    }


def generate_behavior_report(payload, connection=None):
    mode = str(payload.get('mode') or '').lower()
    if mode not in REPORT_SOURCES:
        raise ValueError('mode deve ser tracker, dirijabem ou unified')
    actor = str(payload.get('actor_id') or '').strip()
    if not actor:
        raise ValueError('actor_id é obrigatório')
    timezone_name = payload.get('timezone', 'America/Sao_Paulo')
    period = parse_period(payload.get('from'), payload.get('to'), timezone_name)
    filters = {'from': period.public()['from'], 'to': period.public()['to'], 'timezone': timezone_name, 'mode': mode}
    hash_payload = {'filters': filters, 'actor_id': actor}
    request_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns_connection:
            conn.start_transaction()
        cursor.execute("SELECT public_id,result_json FROM monitoramento.report_runs WHERE request_hash=%s", (request_hash,))
        existing = cursor.fetchone()
        if existing:
            result = json.loads(existing['result_json'])
            result['idempotent_replay'] = True
            return result
        analytics = aggregate_behavior(period, REPORT_SOURCES[mode], connection=conn)
        summary = combine_sources(analytics, mode)
        cursor.execute("SELECT id,version_no FROM monitoramento.report_definitions WHERE report_key='behavior_summary' ORDER BY version_no DESC LIMIT 1")
        definition = cursor.fetchone()
        if not definition:
            raise RuntimeError('Definição de relatório ausente')
        generated_at = datetime.now(timezone.utc).isoformat()
        public_id = str(uuid4())
        public_result = {
            'schema_version': 'behavior-report.v1',
            'public_id': public_id,
            'definition': {'key': 'behavior_summary', 'version': definition['version_no']},
            'formula_version': FORMULA_VERSION,
            'filters': filters,
            'generated_at': generated_at,
            'summary': summary,
            'idempotent_replay': False,
        }
        cursor.execute(
            """INSERT INTO monitoramento.report_runs(
                 public_id,definition_id,request_hash,mode,filters_json,sources_json,
                 result_json,status,row_count,generated_by
               ) VALUES(%s,%s,%s,%s,%s,%s,%s,'completed',%s,%s)""",
            (
                public_id, definition['id'], request_hash, mode, json.dumps(filters),
                json.dumps(list(REPORT_SOURCES[mode])), json.dumps(public_result),
                len(summary['rows']), actor,
            ),
        )
        if owns_connection:
            conn.commit()
        return public_result
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()
