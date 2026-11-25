"""Fila transacional: cria uma vez e avança somente por transições válidas."""

from datetime import datetime,timedelta
import json
from typing import Dict,Optional
from .monitor_db import get_connection

ACTION_TYPES={'internal_notification','send_message','call_owner','notify_authorities','vehicle_command'}
TARGET_TYPES={'operator','contact','authority','vehicle'}
PRIORITIES={'low','normal','high','urgent'}
FINAL={'responded','dead','cancelled','simulated'}
TRANSITIONS={
 ('pending','request_approval'):'awaiting_approval',('pending','approve'):'approved',
 ('pending','claim'):'claimed',('pending','cancel'):'cancelled',('pending','simulate'):'simulated',
 ('awaiting_approval','approve'):'approved',('awaiting_approval','reject'):'cancelled',
 ('awaiting_approval','expire'):'cancelled',('awaiting_approval','cancel'):'cancelled',
 ('approved','claim'):'claimed',('approved','cancel'):'cancelled',
 ('claimed','mark_sent'):'sent',('claimed','fail'):'failed',('claimed','cancel'):'cancelled',
 ('sent','mark_delivered'):'delivered',('sent','mark_responded'):'responded',('sent','fail'):'failed',
 ('delivered','mark_responded'):'responded',('delivered','fail'):'failed',
 ('failed','retry'):'pending',('failed','dead_letter'):'dead',('failed','cancel'):'cancelled',
}

class ActionConflict(ValueError):pass

def plan_transition(action: Dict,command: str,payload: Optional[Dict]=None):
    payload=payload or {};state=action['status'];target=TRANSITIONS.get((state,command))
    if not target:raise ValueError(f'Comando {command} não permitido em {state}')
    attempts=int(action.get('attempt_count',0));maximum=int(action.get('max_attempts',5));updates={'status':target}
    if command=='claim':
        if attempts>=maximum:raise ValueError('Tentativas esgotadas')
        worker=str(payload.get('worker_id') or '').strip();lease=payload.get('lease_seconds',120)
        if not worker or not isinstance(lease,int) or not 10<=lease<=900:raise ValueError('Claim exige worker_id e lease_seconds válidos')
        updates.update(attempt_count=attempts+1,claimed_by=worker,lease_expires_at=datetime.now()+timedelta(seconds=lease))
    if command=='retry':
        if attempts>=maximum:raise ValueError('Retry exige dead_letter apó esgotar tentativas')
        updates.update(available_at=payload.get('available_at') or datetime.now(),last_error_code=None,last_error_message=None,claimed_by=None,lease_expires_at=None)
    if command=='fail':
        code=str(payload.get('error_code') or '').strip()
        if not code:raise ValueError('Falha exige error_code')
        updates.update(last_error_code=code[:100],last_error_message=str(payload.get('error_message') or '')[:1000],claimed_by=None,lease_expires_at=None)
    if target in FINAL:updates.update(completed_at=datetime.now(),claimed_by=None,lease_expires_at=None)
    return updates

def _serialize(row):
    result=dict(row)
    for source,target in [('payload_json','payload'),('policy_snapshot_json','policy_snapshot')]:result[target]=json.loads(result.pop(source))
    for field in ('available_at','lease_expires_at','created_at','completed_at'):
        if isinstance(result.get(field),datetime):result[field]=result[field].isoformat()
    return result

def create_action(payload: Dict,connection=None):
    action_type=payload.get('action_type');target_type=payload.get('target_type');priority=payload.get('priority','normal');incident=payload.get('incident_id');key=str(payload.get('idempotency_key') or '').strip();correlation=str(payload.get('correlation_id') or '').strip();body=payload.get('payload');policy=payload.get('policy_snapshot')
    if action_type not in ACTION_TYPES or target_type not in TARGET_TYPES or priority not in PRIORITIES:raise ValueError('Tipo, alvo ou prioridade inválido')
    if not isinstance(incident,int) or isinstance(incident,bool) or incident<1 or not key or not correlation:raise ValueError('incident_id, idempotency_key e correlation_id obrigatórios')
    if not str(payload.get('target_ref') or '').strip():raise ValueError('target_ref obrigatório')
    if not isinstance(body,dict) or not isinstance(policy,dict):raise ValueError('payload e policy_snapshot devem ser objetos')
    initial=payload.get('status','pending');maximum=payload.get('max_attempts',5)
    if initial not in {'pending','awaiting_approval','simulated'}:raise ValueError('Estado inicial inválido')
    if not isinstance(maximum,int) or isinstance(maximum,bool) or not 1<=maximum<=20:raise ValueError('max_attempts inválido')
    owns=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        if owns:conn.start_transaction()
        cursor.execute("SELECT * FROM monitoramento.action_queue WHERE idempotency_key=%s FOR UPDATE",(key,));existing=cursor.fetchone()
        if existing:
            if existing['incident_id']!=incident:raise ActionConflict('Chave pertence a outro incidente')
            if owns:conn.commit()
            result=_serialize(existing);result['idempotent_replay']=True;return result
        cursor.execute("""INSERT INTO monitoramento.action_queue(public_id,incident_id,agent_run_id,decision_id,action_index,action_type,target_type,target_ref,payload_json,policy_snapshot_json,priority,status,max_attempts,idempotency_key,correlation_id,causation_id) VALUES(UUID(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(incident,payload.get('agent_run_id'),payload.get('decision_id'),payload.get('action_index'),action_type,target_type,str(payload.get('target_ref') or ''),json.dumps(body,separators=(',',':'),sort_keys=True),json.dumps(policy,separators=(',',':'),sort_keys=True),priority,initial,maximum,key,correlation,payload.get('causation_id')));action_id=cursor.lastrowid
        cursor.execute("INSERT INTO monitoramento.action_events(action_id,event_type,from_status,to_status,actor_type,actor_id,details_json,idempotency_key) VALUES(%s,'created',NULL,%s,%s,%s,%s,%s)",(action_id,initial,payload.get('actor_type','system'),payload.get('actor_id'),json.dumps({'priority':priority}),key+':created'))
        cursor.execute("SELECT * FROM monitoramento.action_queue WHERE id=%s",(action_id,));row=cursor.fetchone()
        if owns:conn.commit()
        result=_serialize(row);result['idempotent_replay']=False;return result
    except Exception:
        if owns:conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:conn.close()

def transition_action(public_id: str,command: str,payload: Dict,connection=None):
    expected=payload.get('expected_version');key=str(payload.get('idempotency_key') or '').strip();actor_type=payload.get('actor_type');actor_id=str(payload.get('actor_id') or '').strip() or None
    if not isinstance(expected,int) or isinstance(expected,bool) or expected<1 or not key:raise ValueError('expected_version e idempotency_key obrigatórios')
    if actor_type not in {'system','agent','human','provider'}:raise ValueError('actor_type inválido')
    owns=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        if owns:conn.start_transaction()
        cursor.execute("SELECT * FROM monitoramento.action_queue WHERE public_id=%s FOR UPDATE",(public_id,));action=cursor.fetchone()
        if not action:raise LookupError('Ação não encontrada')
        cursor.execute("SELECT action_id FROM monitoramento.action_events WHERE idempotency_key=%s",(key,));event=cursor.fetchone()
        if event:
            if event['action_id']!=action['id']:raise ActionConflict('Chave pertence a outra ação')
            if owns:conn.commit()
            result=_serialize(action);result['idempotent_replay']=True;return result
        if action['version']!=expected:raise ActionConflict(f'Versão divergente: atual={action["version"]}, esperada={expected}')
        updates=plan_transition(action,command,payload);new_version=expected+1;updates['version']=new_version
        assignments=[];values=[]
        for field,value in updates.items():assignments.append(f'{field}=%s');values.append(value)
        cursor.execute(f"UPDATE monitoramento.action_queue SET {','.join(assignments)} WHERE id=%s AND version=%s",tuple(values+[action['id'],expected]))
        if cursor.rowcount!=1:raise ActionConflict('Ação alterada concorrentemente')
        cursor.execute("INSERT INTO monitoramento.action_events(action_id,event_type,from_status,to_status,actor_type,actor_id,details_json,idempotency_key) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(action['id'],command,action['status'],updates['status'],actor_type,actor_id,json.dumps({k:v for k,v in payload.items() if k not in {'idempotency_key'}},default=str),key))
        cursor.execute("SELECT * FROM monitoramento.action_queue WHERE id=%s",(action['id'],));row=cursor.fetchone()
        if owns:conn.commit()
        result=_serialize(row);result['idempotent_replay']=False;return result
    except Exception:
        if owns:conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:conn.close()


def _action_summary(source, event_type, from_status=None, to_status=None):
    labels = {
        'created': 'Ação criada', 'request_approval': 'Aprovação solicitada',
        'approve': 'Ação aprovada', 'reject': 'Ação rejeitada',
        'expire': 'Aprovação expirada', 'claim': 'Execução iniciada',
        'mark_sent': 'Envio aceito', 'mark_delivered': 'Entrega confirmada',
        'mark_responded': 'Resposta recebida', 'fail': 'Execução falhou',
        'retry': 'Nova tentativa agendada', 'dead_letter': 'Movida para fila de falhas',
        'cancel': 'Ação cancelada', 'simulate': 'Ação simulada',
        'accepted': 'Provedor aceitou', 'sent': 'Provedor enviou',
        'delivered': 'Provedor confirmou entrega', 'read': 'Mensagem lida',
        'responded': 'Destinatário respondeu', 'failed': 'Provedor reportou falha',
        'unknown': 'Evento desconhecido do provedor',
        'owner_confirmed': 'Proprietário confirmou normalidade',
        'owner_denied': 'Proprietário negou a situação',
        'no_answer': 'Ligação sem resposta', 'unclear': 'Resposta de voz inconclusiva',
        'emergency': 'Resposta indicou emergência', 'opt_out': 'Destinatário recusou novos contatos',
        'approval_requested': 'Aprovação humana solicitada',
        'approval_decided': 'Aprovação humana decidida',
    }
    summary = labels.get(event_type, event_type.replace('_', ' ').capitalize())
    if source == 'action' and from_status and to_status:
        summary += f' ({from_status} → {to_status})'
    return summary


def list_incident_action_timeline(incident_id: int, limit=200, connection=None):
    """Compõe timeline segura sem payload, destino, corpo ou credencial."""
    if not isinstance(incident_id, int) or incident_id < 1 or not 1 <= limit <= 1000:
        raise ValueError('incident_id ou limit inválido')
    owns = connection is None; conn = connection or get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT e.id,e.event_type,e.from_status,e.to_status,e.actor_type,e.actor_id,
          e.occurred_at,a.public_id action_public_id,a.action_type,a.correlation_id,a.attempt_count
          FROM monitoramento.action_events e JOIN monitoramento.action_queue a ON a.id=e.action_id
          WHERE a.incident_id=%s ORDER BY e.occurred_at DESC,e.id DESC LIMIT %s""",(incident_id,limit))
        items=[]
        for row in cursor.fetchall():
            items.append({**row,'timeline_id':f'action:{row["id"]}','source':'action',
                'summary':_action_summary('action',row['event_type'],row['from_status'],row['to_status'])})
        cursor.execute("""SELECT p.id,p.normalized_status event_type,NULL from_status,NULL to_status,
          'provider' actor_type,p.provider_code actor_id,p.received_at occurred_at,
          a.public_id action_public_id,a.action_type,a.correlation_id,a.attempt_count
          FROM monitoramento.message_provider_events p JOIN monitoramento.action_queue a ON a.id=p.action_id
          WHERE a.incident_id=%s ORDER BY p.received_at DESC,p.id DESC LIMIT %s""",(incident_id,limit))
        for row in cursor.fetchall():
            items.append({**row,'timeline_id':f'provider:{row["id"]}','source':'provider',
                'summary':_action_summary('provider',row['event_type'])})
        cursor.execute("""SELECT p.id,'approval_requested' event_type,NULL from_status,'awaiting_approval' to_status,
          p.requested_by_type actor_type,p.requested_by actor_id,p.created_at occurred_at,
          a.public_id action_public_id,a.action_type,a.correlation_id,a.attempt_count
          FROM monitoramento.action_approvals p JOIN monitoramento.action_queue a ON a.id=p.action_id
          WHERE a.incident_id=%s ORDER BY p.created_at DESC,p.id DESC LIMIT %s""",(incident_id,limit))
        for row in cursor.fetchall():
            items.append({**row,'timeline_id':f'approval-request:{row["id"]}','source':'approval',
                'summary':_action_summary('approval',row['event_type'])})
        cursor.execute("""SELECT p.id,'approval_decided' event_type,'awaiting_approval' from_status,p.status to_status,
          'human' actor_type,p.decided_by actor_id,p.decided_at occurred_at,
          a.public_id action_public_id,a.action_type,a.correlation_id,a.attempt_count
          FROM monitoramento.action_approvals p JOIN monitoramento.action_queue a ON a.id=p.action_id
          WHERE a.incident_id=%s AND p.decided_at IS NOT NULL
          ORDER BY p.decided_at DESC,p.id DESC LIMIT %s""",(incident_id,limit))
        for row in cursor.fetchall():
            items.append({**row,'timeline_id':f'approval-decision:{row["id"]}','source':'approval',
                'summary':f'{_action_summary("approval",row["event_type"])}: {row["to_status"]}'})
        cursor.execute("""SELECT v.id,v.classification event_type,NULL from_status,NULL to_status,
          'provider' actor_type,v.model_code actor_id,v.created_at occurred_at,
          a.public_id action_public_id,a.action_type,a.correlation_id,a.attempt_count
          FROM monitoramento.voice_response_analyses v
          JOIN monitoramento.action_queue a ON a.id=v.action_id
          WHERE a.incident_id=%s ORDER BY v.created_at DESC,v.id DESC LIMIT %s""",(incident_id,limit))
        for row in cursor.fetchall():
            items.append({**row,'timeline_id':f'voice:{row["id"]}','source':'provider',
                'summary':_action_summary('voice',row['event_type'])})
        items.sort(key=lambda item:(item['occurred_at'],item['timeline_id']))
        total=len(items); selected=items[-limit:]
        return [_serialize_timeline(item) for item in selected],total,total>len(selected)
    finally:
        cursor.close()
        if owns:conn.close()


def _serialize_timeline(item):
    result={key:value for key,value in item.items() if key!='id'}
    if isinstance(result.get('occurred_at'),datetime):result['occurred_at']=result['occurred_at'].isoformat()
    return result
