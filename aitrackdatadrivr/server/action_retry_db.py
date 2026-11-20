"""Backoff, recuperação de lease, dead-letter e reprocessamento manual."""

from datetime import datetime, timedelta
import hashlib
import json
import logging
import time

from .action_queue_db import create_action, transition_action
from .monitor_db import get_connection

logger = logging.getLogger(__name__)


def calculate_backoff(attempt_count, stable_key, base_seconds=30, cap_seconds=3600):
    if not isinstance(attempt_count, int) or attempt_count < 1:
        raise ValueError('attempt_count inválido')
    raw = min(cap_seconds, base_seconds * (2 ** (attempt_count - 1)))
    jitter = int(hashlib.sha256(str(stable_key).encode()).hexdigest()[:4], 16) % max(1, raw // 10 + 1)
    return min(cap_seconds, raw + jitter)


def recover_expired_claims(limit=100, now=None):
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError('limit inválido')
    now = now or datetime.now(); conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("""SELECT * FROM monitoramento.action_queue
          WHERE status='claimed' AND lease_expires_at<=%s
          ORDER BY lease_expires_at,id LIMIT %s FOR UPDATE""",(now,limit))
        rows=cursor.fetchall();result={'retried':0,'dead':0}
        for action in rows:
            failed=transition_action(action['public_id'],'fail',{
                'expected_version':action['version'],
                'idempotency_key':f'{action["idempotency_key"]}:lease:{action["version"]}:failed',
                'actor_type':'system','actor_id':'action-retry-worker',
                'error_code':'LEASE_EXPIRED','error_message':'Worker não concluiu antes do lease',
            },connection=conn)
            if int(failed['attempt_count']) >= int(failed['max_attempts']):
                transition_action(action['public_id'],'dead_letter',{
                    'expected_version':failed['version'],
                    'idempotency_key':f'{action["idempotency_key"]}:lease:{action["version"]}:dead',
                    'actor_type':'system','actor_id':'action-retry-worker',
                },connection=conn);result['dead']+=1
            else:
                delay=calculate_backoff(int(failed['attempt_count']),action['public_id'])
                transition_action(action['public_id'],'retry',{
                    'expected_version':failed['version'],
                    'idempotency_key':f'{action["idempotency_key"]}:lease:{action["version"]}:retry',
                    'actor_type':'system','actor_id':'action-retry-worker',
                    'available_at':now+timedelta(seconds=delay),
                },connection=conn);result['retried']+=1
        conn.commit();return {**result,'processed':len(rows)}
    except Exception:
        conn.rollback();raise
    finally:cursor.close();conn.close()


def reprocess_dead_action(public_id, actor_id, reason, idempotency_key):
    actor=str(actor_id or '').strip();reason=str(reason or '').strip();key=str(idempotency_key or '').strip()
    if not actor or len(reason)<5 or not key:
        raise ValueError('actor_id, motivo e idempotência obrigatórios')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.action_queue WHERE public_id=%s FOR UPDATE",(public_id,));original=cursor.fetchone()
        if not original:raise LookupError('Ação não encontrada')
        cursor.execute("""SELECT r.*,a.public_id replacement_public_id FROM monitoramento.action_reprocess_audit r
          JOIN monitoramento.action_queue a ON a.id=r.replacement_action_id WHERE r.idempotency_key=%s""",(key,));existing=cursor.fetchone()
        if existing:
            conn.commit();existing['idempotent_replay']=True;return existing
        if original['status']!='dead':raise ValueError('Somente ação em dead-letter pode ser reprocessada')
        replacement=create_action({
            'incident_id':original['incident_id'],'agent_run_id':original['agent_run_id'],
            'action_type':original['action_type'],'target_type':original['target_type'],
            'target_ref':original['target_ref'],'payload':json.loads(original['payload_json']),
            'policy_snapshot':json.loads(original['policy_snapshot_json']),
            'priority':original['priority'],'max_attempts':original['max_attempts'],
            'idempotency_key':f'manual-reprocess:{key}','correlation_id':original['correlation_id'],
            'causation_id':original['public_id'],'actor_type':'human','actor_id':actor,
        },connection=conn)
        cursor.execute("""INSERT INTO monitoramento.action_reprocess_audit
          (original_action_id,replacement_action_id,actor_id,reason,idempotency_key)
          VALUES(%s,%s,%s,%s,%s)""",(original['id'],replacement['id'],actor,reason,key))
        audit_id=cursor.lastrowid;conn.commit();return {'id':audit_id,'original_public_id':public_id,
          'replacement_public_id':replacement['public_id'],'idempotent_replay':False}
    except Exception:
        conn.rollback();raise
    finally:cursor.close();conn.close()


def run_retry_worker(interval_seconds=15):
    while True:
        try:
            result=recover_expired_claims()
            if result['processed']:logger.info('Ações com lease expirado processadas: %s',result)
        except Exception:
            logger.exception('Falha recuperando leases da fila de ações')
        time.sleep(interval_seconds)
