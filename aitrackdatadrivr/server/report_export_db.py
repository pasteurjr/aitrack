"""Jobs de exportação interna e agendas bloqueadas até autenticação/RBAC."""

import hashlib
import json
from uuid import uuid4

from .monitor_db import get_connection
from .report_export import FORMATS, next_schedule_run, serialize_report
from .report_service import generate_behavior_report


def create_manual_export(payload, connection=None):
    actor = str(payload.get('actor_id') or '').strip()
    key = str(payload.get('idempotency_key') or '').strip()
    export_format = str(payload.get('format') or '').lower()
    if not actor or not key or export_format not in FORMATS:
        raise ValueError('actor_id, idempotency_key e format csv/json são obrigatórios')
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns:
            conn.start_transaction()
        cursor.execute('SELECT * FROM monitoramento.report_export_jobs WHERE idempotency_key=%s', (key,))
        existing = cursor.fetchone()
        report = generate_behavior_report(payload, connection=conn)
        artifact, row_count = serialize_report(report, export_format)
        digest = hashlib.sha256(artifact).hexdigest()
        if existing:
            if existing['artifact_sha256'] != digest:
                raise ValueError('idempotency_key reutilizada com artefato divergente')
            return _result(existing, artifact, True)
        cursor.execute('SELECT id FROM monitoramento.report_runs WHERE public_id=%s', (report['public_id'],))
        report_run = cursor.fetchone()
        public_id = str(uuid4())
        artifact_ref = f'internal://report-exports/{public_id}.{export_format}'
        cursor.execute(
            """INSERT INTO monitoramento.report_export_jobs(
                 public_id,report_run_id,format,status,idempotency_key,permission_snapshot_json,
                 artifact_ref,artifact_sha256,artifact_size_bytes,row_count,created_by
               ) VALUES(%s,%s,%s,'completed',%s,%s,%s,%s,%s,%s,%s)""",
            (public_id, report_run['id'], export_format, key,
             json.dumps({'scope': 'internal_download', 'auth_status': 'pending_ui_8_1'}),
             artifact_ref, digest, len(artifact), row_count, actor),
        )
        job_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO monitoramento.report_export_events(
                 job_id,event_type,actor_id,details_json,idempotency_key
               ) VALUES(%s,'generated',%s,%s,%s)""",
            (job_id, actor, json.dumps({'sha256': digest, 'size_bytes': len(artifact), 'delivery': 'internal_only'}), key + ':generated'),
        )
        if owns:
            conn.commit()
        cursor.execute('SELECT * FROM monitoramento.report_export_jobs WHERE id=%s', (job_id,))
        return _result(cursor.fetchone(), artifact, False)
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()


def _result(row, artifact, replay):
    return {
        'schema_version': 'report-export.v1',
        'public_id': row['public_id'],
        'status': row['status'],
        'format': row['format'],
        'artifact_ref': row['artifact_ref'],
        'artifact_sha256': row['artifact_sha256'],
        'artifact_size_bytes': int(row['artifact_size_bytes']),
        'row_count': int(row['row_count']),
        'content': artifact.decode('utf-8'),
        'delivery': 'internal_download',
        'idempotent_replay': replay,
    }


def create_blocked_schedule(payload, connection=None):
    actor = str(payload.get('actor_id') or '').strip()
    mode = str(payload.get('mode') or '').lower()
    export_format = str(payload.get('format') or '').lower()
    timezone_name = str(payload.get('timezone') or '')
    cadence = str(payload.get('cadence') or '')
    local_time = str(payload.get('local_time') or '')
    if not actor or mode not in {'tracker', 'dirijabem', 'unified'} or export_format not in FORMATS:
        raise ValueError('ator, modo e formato válidos são obrigatórios')
    calculated_next = next_schedule_run(cadence, local_time, timezone_name, payload.get('weekday'))
    owns = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if owns:
            conn.start_transaction()
        cursor.execute("SELECT id FROM monitoramento.report_definitions WHERE report_key='behavior_summary' ORDER BY version_no DESC LIMIT 1")
        definition = cursor.fetchone()
        public_id = str(uuid4())
        cursor.execute(
            """INSERT INTO monitoramento.report_export_schedules(
                 public_id,report_definition_id,mode,format,filters_json,timezone_name,
                 cadence,local_time,weekday,destination_ref,status,next_run_at,created_by
               ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'internal:operator','blocked_auth',NULL,%s)""",
            (public_id, definition['id'], mode, export_format,
             json.dumps(payload.get('filters') or {}), timezone_name, cadence,
             local_time, payload.get('weekday'), actor),
        )
        if owns:
            conn.commit()
        return {
            'schema_version': 'report-export-schedule.v1', 'public_id': public_id,
            'status': 'blocked_auth', 'next_run_at': None,
            'calculated_next_run_at': calculated_next.isoformat(),
            'block_reason': 'AUTH_AND_RBAC_REQUIRED',
        }
    except Exception:
        if owns:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:
            conn.close()
