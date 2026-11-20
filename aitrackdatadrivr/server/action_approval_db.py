"""Solicitação e decisão humana independente para ações acima da autonomia."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from .action_queue_db import ActionConflict, transition_action
from .monitor_db import get_connection

ROLES = {'supervisor', 'security_manager', 'administrator'}


@dataclass(frozen=True)
class ApproverIdentity:
    actor_id: str
    role: str


def validate_approver(identity, approval, now=None):
    now = now or datetime.now()
    if not isinstance(identity, ApproverIdentity) or identity.role not in ROLES:
        raise PermissionError('Identidade de aprovador inválida')
    if identity.actor_id == approval['requested_by']:
        raise PermissionError('Autoaprovação não permitida')
    if identity.role != approval['required_role'] and identity.role != 'administrator':
        raise PermissionError('Papel insuficiente para aprovação')
    if approval['expires_at'] <= now:
        raise ValueError('Solicitação expirada')


def request_approval(action_public_id, payload):
    requester = str(payload.get('requested_by') or '').strip()
    reason = str(payload.get('reason') or '').strip()
    role = payload.get('required_role')
    ttl = payload.get('ttl_seconds', 900)
    requester_type = payload.get('requested_by_type', 'agent')
    if (not requester or not reason or role not in ROLES
            or requester_type not in {'agent', 'human', 'system'}
            or not isinstance(ttl, int) or not 60 <= ttl <= 86400):
        raise ValueError('solicitante, motivo, papel e ttl válidos são obrigatórios')
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("SELECT * FROM monitoramento.action_queue WHERE public_id=%s FOR UPDATE", (action_public_id,))
        action = cursor.fetchone()
        if not action: raise LookupError('Ação não encontrada')
        cursor.execute("SELECT * FROM monitoramento.action_approvals WHERE action_id=%s", (action['id'],))
        existing = cursor.fetchone()
        if existing:
            conn.commit(); return {**existing, 'idempotent_replay': True}
        moved = transition_action(action_public_id, 'request_approval', {
            'expected_version': action['version'], 'idempotency_key': f'{action["idempotency_key"]}:approval:requested',
            'actor_type': payload.get('requested_by_type', 'agent'), 'actor_id': requester,
        }, connection=conn)
        expires = datetime.now() + timedelta(seconds=ttl)
        cursor.execute("""INSERT INTO monitoramento.action_approvals
          (public_id,action_id,action_version_requested,required_role,requested_by_type,
           requested_by,request_reason,policy_snapshot_json,expires_at)
          VALUES(UUID(),%s,%s,%s,%s,%s,%s,%s,%s)""", (
            action['id'], moved['version'], role, requester_type,
            requester, reason, json.dumps(payload.get('policy_snapshot') or {}, separators=(',',':'),sort_keys=True), expires))
        aid=cursor.lastrowid; cursor.execute("SELECT * FROM monitoramento.action_approvals WHERE id=%s",(aid,)); result=cursor.fetchone()
        conn.commit(); result['idempotent_replay']=False; return result
    except Exception:
        conn.rollback(); raise
    finally: cursor.close(); conn.close()


def decide_approval(public_id, decision, reason, idempotency_key, identity, expected_version):
    if decision not in {'approved','rejected'} or not str(reason).strip() or not str(idempotency_key).strip():
        raise ValueError('decisão, motivo e idempotência obrigatórios')
    conn=get_connection(); cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction(); cursor.execute("SELECT * FROM monitoramento.action_approvals WHERE public_id=%s FOR UPDATE",(public_id,)); approval=cursor.fetchone()
        if not approval: raise LookupError('Aprovação não encontrada')
        if approval['decision_idempotency_key']==idempotency_key:
            conn.commit(); approval['idempotent_replay']=True; return approval
        if approval['status']!='pending' or approval['version']!=expected_version: raise ActionConflict('Aprovação já decidida ou versão divergente')
        validate_approver(identity,approval)
        cursor.execute("SELECT public_id,version,idempotency_key FROM monitoramento.action_queue WHERE id=%s FOR UPDATE",(approval['action_id'],)); action=cursor.fetchone()
        command='approve' if decision=='approved' else 'reject'
        transition_action(action['public_id'],command,{'expected_version':action['version'],'idempotency_key':f'{action["idempotency_key"]}:approval:{idempotency_key}','actor_type':'human','actor_id':identity.actor_id},connection=conn)
        cursor.execute("""UPDATE monitoramento.action_approvals SET status=%s,decided_by=%s,decided_role=%s,
          decision_reason=%s,decision_idempotency_key=%s,decided_at=CURRENT_TIMESTAMP(6),version=version+1
          WHERE id=%s AND version=%s""",(decision,identity.actor_id,identity.role,reason,idempotency_key,approval['id'],expected_version))
        cursor.execute("SELECT * FROM monitoramento.action_approvals WHERE id=%s",(approval['id'],));result=cursor.fetchone();conn.commit();result['idempotent_replay']=False;return result
    except Exception:
        conn.rollback();raise
    finally:cursor.close();conn.close()


def expire_due_approvals(limit=100):
    """Expira solicitações vencidas e cancela as ações ainda bloqueadas."""
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError('limit inválido')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("""SELECT p.id approval_id,p.version approval_version,
          a.public_id,a.version action_version,a.idempotency_key
          FROM monitoramento.action_approvals p
          JOIN monitoramento.action_queue a ON a.id=p.action_id
          WHERE p.status='pending' AND p.expires_at<=CURRENT_TIMESTAMP(6)
            AND a.status='awaiting_approval'
          ORDER BY p.expires_at,p.id LIMIT %s FOR UPDATE""",(limit,))
        rows=cursor.fetchall()
        for row in rows:
            transition_action(row['public_id'],'expire',{
                'expected_version':row['action_version'],
                'idempotency_key':f'{row["idempotency_key"]}:approval:expired',
                'actor_type':'system','actor_id':'approval-expirer',
            },connection=conn)
            cursor.execute("""UPDATE monitoramento.action_approvals SET status='expired',
              decided_by='approval-expirer',decided_role='system',
              decision_reason='Prazo de aprovação expirado',decided_at=CURRENT_TIMESTAMP(6),
              version=version+1 WHERE id=%s AND version=%s""",
              (row['approval_id'],row['approval_version']))
        conn.commit();return len(rows)
    except Exception:
        conn.rollback();raise
    finally:cursor.close();conn.close()
