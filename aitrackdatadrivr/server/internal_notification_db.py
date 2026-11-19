"""Entrega local transacional; nenhuma rede ou contato externo."""

from datetime import datetime
from typing import Dict
from .action_queue_db import create_action,transition_action,ActionConflict
from .monitor_db import get_connection

def _serialize(row):
    result=dict(row)
    for field in ('read_at','created_at'):
        if isinstance(result.get(field),datetime):result[field]=result[field].isoformat()
    result['unread']=result.get('read_at') is None
    return result

def create_notification(payload: Dict,connection=None):
    incident=payload.get('incident_id');recipient=str(payload.get('recipient_ref') or '').strip();title=str(payload.get('title') or '').strip();body=str(payload.get('body') or '').strip();priority=payload.get('priority','normal');key=str(payload.get('idempotency_key') or '').strip();correlation=str(payload.get('correlation_id') or '').strip()
    if not recipient or not 3<=len(title)<=200 or not 5<=len(body)<=5000:raise ValueError('recipient_ref, title e body válidos são obrigatórios')
    owns=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        if owns:conn.start_transaction()
        action=create_action({'incident_id':incident,'action_type':'internal_notification','target_type':'operator','target_ref':recipient,'payload':{'title':title,'body':body},'policy_snapshot':payload.get('policy_snapshot') or {'channel':'internal','external':False},'priority':priority,'idempotency_key':key,'correlation_id':correlation,'actor_type':payload.get('actor_type','system'),'actor_id':payload.get('actor_id')},connection=conn)
        cursor.execute("SELECT n.*,a.public_id action_public_id,a.version action_version FROM monitoramento.internal_notifications n JOIN monitoramento.action_queue a ON a.id=n.action_id WHERE n.action_id=%s",(action['id'],));existing=cursor.fetchone()
        if existing:
            if owns:conn.commit()
            result=_serialize(existing);result['idempotent_replay']=True;return result
        claimed=transition_action(action['public_id'],'claim',{'expected_version':action['version'],'idempotency_key':key+':claim','actor_type':'system','actor_id':'internal-notification','worker_id':'internal-notification','lease_seconds':30},connection=conn)
        sent=transition_action(action['public_id'],'mark_sent',{'expected_version':claimed['version'],'idempotency_key':key+':sent','actor_type':'system','actor_id':'internal-notification'},connection=conn)
        delivered=transition_action(action['public_id'],'mark_delivered',{'expected_version':sent['version'],'idempotency_key':key+':delivered','actor_type':'system','actor_id':'internal-notification'},connection=conn)
        cursor.execute("INSERT INTO monitoramento.internal_notifications(public_id,action_id,incident_id,recipient_ref,title,body,priority) VALUES(UUID(),%s,%s,%s,%s,%s,%s)",(action['id'],incident,recipient,title,body,priority));notification=cursor.lastrowid
        cursor.execute("SELECT n.*,a.public_id action_public_id,a.version action_version FROM monitoramento.internal_notifications n JOIN monitoramento.action_queue a ON a.id=n.action_id WHERE n.id=%s",(notification,));row=cursor.fetchone()
        if owns:conn.commit()
        result=_serialize(row);result['idempotent_replay']=False;return result
    except Exception:
        if owns:conn.rollback()
        raise
    finally:
        cursor.close()
        if owns:conn.close()

def list_notifications(recipient_ref: str,unread_only=False,limit=100):
    if not recipient_ref or not 1<=limit<=200:raise ValueError('recipient_ref e limit inválidos')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT n.*,a.public_id action_public_id,a.version action_version FROM monitoramento.internal_notifications n JOIN monitoramento.action_queue a ON a.id=n.action_id WHERE n.recipient_ref=%s"+(" AND n.read_at IS NULL" if unread_only else "")+" ORDER BY n.created_at DESC,n.id DESC LIMIT %s",(recipient_ref,limit));return [_serialize(row) for row in cursor.fetchall()]
    finally:cursor.close();conn.close()

def mark_read(public_id: str,payload: Dict):
    expected=payload.get('expected_version');actor=str(payload.get('actor_id') or '').strip();key=str(payload.get('idempotency_key') or '').strip()
    if not isinstance(expected,int) or not actor or not key:raise ValueError('expected_version, actor_id e idempotency_key obrigatórios')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT n.*,a.public_id action_public_id,a.version action_version FROM monitoramento.internal_notifications n JOIN monitoramento.action_queue a ON a.id=n.action_id WHERE n.public_id=%s FOR UPDATE",(public_id,));row=cursor.fetchone()
        if not row:raise LookupError('Notificação não encontrada')
        if row['read_idempotency_key']==key:conn.commit();result=_serialize(row);result['idempotent_replay']=True;return result
        if row['read_at'] is not None or row['version']!=expected:raise ActionConflict('Notificação já lida ou versão divergente')
        transition_action(row['action_public_id'],'mark_responded',{'expected_version':row['action_version'],'idempotency_key':key+':action','actor_type':'human','actor_id':actor},connection=conn)
        cursor.execute("UPDATE monitoramento.internal_notifications SET read_at=CURRENT_TIMESTAMP(6),read_by=%s,read_idempotency_key=%s,version=version+1 WHERE id=%s AND version=%s",(actor,key,row['id'],expected))
        cursor.execute("SELECT n.*,a.public_id action_public_id,a.version action_version FROM monitoramento.internal_notifications n JOIN monitoramento.action_queue a ON a.id=n.action_id WHERE n.id=%s",(row['id'],));result=_serialize(cursor.fetchone());conn.commit();result['idempotent_replay']=False;return result
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()
