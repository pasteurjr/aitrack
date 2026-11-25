"""Atribuição de rota e máquina de execução temporal."""

from datetime import datetime,timezone
import json
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from .monitor_db import get_connection

TRANSITIONS={('scheduled','start'):'active',('scheduled','cancel'):'cancelled',('scheduled','expire'):'expired',('active','complete'):'completed',('active','cancel'):'cancelled',('active','fail'):'failed'}
TERMINAL={'completed','cancelled','expired','failed'}

def parse_instant(value,field):
    if not isinstance(value,str):raise ValueError(f'{field} deve ser ISO-8601 com fuso')
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:raise ValueError(f'{field} inválido') from exc
    if parsed.tzinfo is None:raise ValueError(f'{field} exige fuso')
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)

def validate_window(start,end,timezone_name):
    try:ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError,ValueError) as exc:raise ValueError('timezone_name inválido') from exc
    start_utc=parse_instant(start,'start');end_utc=parse_instant(end,'end')
    if end_utc<=start_utc or (end_utc-start_utc).days>31:raise ValueError('Janela deve ser positiva e ter no máximo 31 dias')
    return start_utc,end_utc

def plan_execution_transition(status,command):
    target=TRANSITIONS.get((status,command))
    if not target:raise ValueError(f'Comando {command} não permitido em {status}')
    return target

def create_assignment(route_public_id,payload):
    vehicle=payload.get('vehicle_id');driver=payload.get('driver_id');actor=str(payload.get('actor_id') or '').strip();tz=str(payload.get('timezone_name') or '').strip()
    if (vehicle is None)==(driver is None) or not actor:raise ValueError('Exatamente um alvo e actor_id são obrigatórios')
    start,end=validate_window(payload.get('valid_from'),payload.get('valid_until'),tz);conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT id,version FROM monitoramento.routes WHERE public_id=%s AND status='active' FOR UPDATE",(route_public_id,));route=cursor.fetchone()
        if not route:raise LookupError('Rota ativa não encontrada')
        version=payload.get('route_version',route['version']);cursor.execute("SELECT id FROM monitoramento.route_versions WHERE route_id=%s AND version_no=%s",(route['id'],version));route_version=cursor.fetchone()
        if not route_version:raise LookupError('Versão da rota não encontrada')
        field='vehicle_id' if vehicle is not None else 'driver_id';target=vehicle if vehicle is not None else driver
        cursor.execute(f"""SELECT id FROM monitoramento.route_assignments WHERE {field}=%s AND active=TRUE
          AND valid_from<%s AND valid_until>%s FOR UPDATE""",(target,end,start))
        if cursor.fetchone():raise ValueError('Alvo já possui atribuição sobreposta')
        cursor.execute("""INSERT INTO monitoramento.route_assignments(public_id,route_version_id,vehicle_id,driver_id,timezone_name,valid_from,valid_until,created_by)
          VALUES(UUID(),%s,%s,%s,%s,%s,%s,%s)""",(route_version['id'],vehicle,driver,tz,start,end,actor));aid=cursor.lastrowid
        cursor.execute("SELECT public_id FROM monitoramento.route_assignments WHERE id=%s",(aid,));public_id=cursor.fetchone()['public_id'];conn.commit();return {'id':aid,'public_id':public_id,'route_version_id':route_version['id'],'target_type':'vehicle' if vehicle else 'driver','target_id':target,'timezone_name':tz,'valid_from':start.isoformat(),'valid_until':end.isoformat(),'version':1}
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()

def create_execution(assignment_public_id,payload):
    key=str(payload.get('idempotency_key') or '').strip();start=parse_instant(payload.get('planned_start_at'),'planned_start_at');end=parse_instant(payload.get('planned_end_at'),'planned_end_at')
    if not key or end<=start:raise ValueError('idempotency_key e janela válida obrigatórios')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.route_assignments WHERE public_id=%s AND active=TRUE FOR UPDATE",(assignment_public_id,));assignment=cursor.fetchone()
        if not assignment:raise LookupError('Atribuição não encontrada')
        if start<assignment['valid_from'] or end>assignment['valid_until']:raise ValueError('Execução fora da vigência')
        cursor.execute("SELECT id,public_id,status FROM monitoramento.route_executions WHERE idempotency_key=%s",(key,));existing=cursor.fetchone()
        if existing:conn.commit();existing['idempotent_replay']=True;return existing
        cursor.execute("""INSERT INTO monitoramento.route_executions(public_id,assignment_id,route_version_id,planned_start_at,planned_end_at,idempotency_key)
          VALUES(UUID(),%s,%s,%s,%s,%s)""",(assignment['id'],assignment['route_version_id'],start,end,key));eid=cursor.lastrowid
        cursor.execute("INSERT INTO monitoramento.route_execution_timeline(execution_id,event_type,from_status,to_status,actor_id,details_json,idempotency_key) VALUES(%s,'created',NULL,'scheduled',%s,'{}',%s)",(eid,payload.get('actor_id','system'),key+':created'))
        cursor.execute("SELECT public_id FROM monitoramento.route_executions WHERE id=%s",(eid,));public_id=cursor.fetchone()['public_id'];conn.commit();return {'id':eid,'public_id':public_id,'status':'scheduled','version':1,'idempotent_replay':False}
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()

def transition_execution(public_id,command,payload):
    expected=payload.get('expected_version');key=str(payload.get('idempotency_key') or '').strip();actor=str(payload.get('actor_id') or '').strip()
    if not isinstance(expected,int) or expected<1 or not key or not actor:raise ValueError('versão, idempotência e ator obrigatórios')
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.route_executions WHERE public_id=%s FOR UPDATE",(public_id,));execution=cursor.fetchone()
        if not execution:raise LookupError('Execução não encontrada')
        cursor.execute("SELECT id FROM monitoramento.route_execution_timeline WHERE idempotency_key=%s",(key,));existing=cursor.fetchone()
        if existing:conn.commit();return {'public_id':public_id,'status':execution['status'],'version':execution['version'],'idempotent_replay':True}
        if execution['version']!=expected:raise ValueError('Versão divergente')
        target=plan_execution_transition(execution['status'],command);fields=['status=%s','version=version+1'];values=[target]
        if command=='start':fields.append('started_at=CURRENT_TIMESTAMP(6)')
        if target in TERMINAL:fields.append('completed_at=CURRENT_TIMESTAMP(6)')
        cursor.execute(f"UPDATE monitoramento.route_executions SET {','.join(fields)} WHERE id=%s AND version=%s",tuple(values+[execution['id'],expected]))
        cursor.execute("INSERT INTO monitoramento.route_execution_timeline(execution_id,event_type,from_status,to_status,actor_id,details_json,idempotency_key) VALUES(%s,%s,%s,%s,%s,%s,%s)",(execution['id'],command,execution['status'],target,actor,json.dumps(payload.get('details') or {}),key));conn.commit();return {'public_id':public_id,'status':target,'version':expected+1,'idempotent_replay':False}
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()
