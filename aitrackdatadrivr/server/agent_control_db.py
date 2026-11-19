"""Pausa e takeover humano atômicos, versionados e auditáveis."""

from datetime import datetime
from typing import Dict

from .incident_db import transition_incident
from .monitor_db import get_connection


class AgentControlConflict(ValueError):pass


TRANSITIONS={('active','pause'):'paused',('paused','resume'):'active',
             ('active','takeover'):'human_owned',('paused','takeover'):'human_owned',
             ('human_owned','release'):'active'}


def plan_control(state: str,command: str):
    target=TRANSITIONS.get((state,command))
    if not target:raise ValueError(f'Comando {command} não permitido em {state}')
    return target


def _serialize(row):
    result=dict(row)
    if isinstance(result.get('updated_at'),datetime):result['updated_at']=result['updated_at'].isoformat()
    return result


def get_control(incident_id: int):
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM monitoramento.agent_incident_controls WHERE incident_id=%s",(incident_id,))
        row=cursor.fetchone()
        return _serialize(row) if row else {'incident_id':incident_id,'control_state':'active','version':1,'human_owner_id':None,'reason':None,'implicit':True}
    finally:cursor.close();conn.close()


def transition_control(incident_id: int,command: str,payload: Dict,connection=None):
    expected=payload.get('expected_version');actor_id=str(payload.get('actor_id') or '').strip();actor_name=str(payload.get('actor_name') or '').strip();reason=str(payload.get('reason') or '').strip();key=str(payload.get('idempotency_key') or '').strip();correlation=str(payload.get('correlation_id') or '').strip() or None
    if not isinstance(expected,int) or isinstance(expected,bool) or expected<1:raise ValueError('expected_version inválido')
    if not actor_id or not actor_name or len(reason)<5 or not key:raise ValueError('ator, motivo e idempotency_key são obrigatórios')
    owns_connection=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        if owns_connection:conn.start_transaction()
        cursor.execute("SELECT id,version FROM monitoramento.incidents WHERE id=%s FOR UPDATE",(incident_id,));incident=cursor.fetchone()
        if not incident:raise LookupError('Incidente não encontrado')
        cursor.execute("SELECT incident_id FROM monitoramento.agent_incident_control_audit WHERE idempotency_key=%s",(key,));replay=cursor.fetchone()
        if replay:
            if replay['incident_id']!=incident_id:raise AgentControlConflict('Chave pertence a outro incidente')
            cursor.execute("SELECT * FROM monitoramento.agent_incident_controls WHERE incident_id=%s",(incident_id,));row=cursor.fetchone()
            if owns_connection:conn.commit()
            result=_serialize(row);result['idempotent_replay']=True;return result
        cursor.execute("SELECT * FROM monitoramento.agent_incident_controls WHERE incident_id=%s FOR UPDATE",(incident_id,));control=cursor.fetchone()
        if not control:
            cursor.execute("INSERT INTO monitoramento.agent_incident_controls(incident_id) VALUES(%s)",(incident_id,));control={'incident_id':incident_id,'control_state':'active','version':1,'agent_id':None}
        if int(control['version'])!=expected:raise AgentControlConflict(f'Versão divergente: atual={control["version"]}, esperada={expected}')
        target=plan_control(control['control_state'],command);new_version=expected+1
        if command=='takeover':
            transition_incident(incident_id,'takeover',{'assigned_type':'human','assigned_to':actor_id,'summary':f'{actor_name} assumiu controle do agente','correlation_id':correlation},{'type':'human','id':actor_id,'name':actor_name},incident['version'],key+':incident',connection=conn)
        cursor.execute("UPDATE monitoramento.agent_incident_controls SET control_state=%s,version=%s,human_owner_id=%s,reason=%s,updated_at=CURRENT_TIMESTAMP(6) WHERE incident_id=%s AND version=%s",(target,new_version,actor_id if target=='human_owned' else None,reason,incident_id,expected))
        if cursor.rowcount!=1:raise AgentControlConflict('Controle alterado concorrentemente')
        cursor.execute("INSERT INTO monitoramento.agent_incident_control_audit(incident_id,from_state,to_state,actor_id,actor_name,reason,idempotency_key,correlation_id,version) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(incident_id,control['control_state'],target,actor_id,actor_name,reason,key,correlation,new_version))
        cursor.execute("SELECT * FROM monitoramento.agent_incident_controls WHERE incident_id=%s",(incident_id,));result=_serialize(cursor.fetchone())
        if owns_connection:conn.commit()
        result['idempotent_replay']=False;return result
    except Exception:
        if owns_connection:conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:conn.close()
