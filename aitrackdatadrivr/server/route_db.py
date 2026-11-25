"""CRUD versionado das rotas operacionais."""

import json
from decimal import Decimal
from .monitor_db import get_connection
from .route_geometry import normalize_route_geometry
from .tenant_scope import current_tenant_id

class RouteConflict(ValueError):pass

def _row(row):
    result=dict(row)
    if isinstance(result.get('geometry_json'),str):result['geometry']=json.loads(result.pop('geometry_json'))
    for field in ('created_at','updated_at'):
        if result.get(field):result[field]=result[field].isoformat()
    for field,value in list(result.items()):
        if isinstance(value,Decimal):result[field]=float(value)
    return result

def list_routes(include_archived=False,limit=100):
    if not 1<=limit<=200:raise ValueError('limit inválido')
    tenant_id=current_tenant_id(required=False);conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT r.*,v.id route_version_id,v.version_no,v.geometry_json,v.geometry_sha256,
          v.corridor_meters,v.length_meters FROM monitoramento.routes r
          JOIN monitoramento.route_versions v ON v.route_id=r.id AND v.version_no=r.version
          WHERE (%s OR r.status='active') AND (%s IS NULL OR r.tenant_id=%s)
          ORDER BY r.updated_at DESC,r.id DESC LIMIT %s""",(include_archived,tenant_id,tenant_id,limit))
        return [_row(item) for item in cursor.fetchall()]
    finally:cursor.close();conn.close()

def get_route(public_id,connection=None):
    tenant_id=current_tenant_id(required=False);owns=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT r.*,v.id route_version_id,v.version_no,v.geometry_json,v.geometry_sha256,
          v.corridor_meters,v.length_meters FROM monitoramento.routes r
          JOIN monitoramento.route_versions v ON v.route_id=r.id AND v.version_no=r.version
          WHERE r.public_id=%s AND (%s IS NULL OR r.tenant_id=%s)""",(public_id,tenant_id,tenant_id));value=cursor.fetchone();return _row(value) if value else None
    finally:cursor.close();owns and conn.close()

def create_route(payload):
    name=str(payload.get('name') or '').strip();description=str(payload.get('description') or '').strip() or None;actor=str(payload.get('actor_id') or '').strip();reason=str(payload.get('reason') or '').strip()
    if not 2<=len(name)<=150 or not actor or not reason:raise ValueError('name, actor_id e reason obrigatórios')
    tenant_id=current_tenant_id(required=False);normalized=normalize_route_geometry(payload.get('geometry'),payload.get('corridor_meters'))
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("INSERT INTO monitoramento.routes(tenant_id,public_id,name,description,created_by) VALUES(%s,UUID(),%s,%s,%s)",(tenant_id,name,description,actor));route_id=cursor.lastrowid
        cursor.execute("""INSERT INTO monitoramento.route_versions(route_id,version_no,geometry_json,geometry_sha256,corridor_meters,length_meters,created_by,change_reason)
          VALUES(%s,1,%s,%s,%s,%s,%s,%s)""",(route_id,normalized['geometry_json'],normalized['geometry_sha256'],normalized['corridor_meters'],normalized['length_meters'],actor,reason))
        cursor.execute("INSERT INTO monitoramento.route_audit_log(route_id,event_type,actor_id,reason,snapshot_json) VALUES(%s,'created',%s,%s,%s)",(route_id,actor,reason,json.dumps({'name':name,'geometry_sha256':normalized['geometry_sha256']})))
        cursor.execute("SELECT public_id FROM monitoramento.routes WHERE id=%s",(route_id,));public_id=cursor.fetchone()['public_id'];conn.commit();return get_route(public_id)
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()

def update_route(public_id,payload):
    expected=payload.get('expected_version');actor=str(payload.get('actor_id') or '').strip();reason=str(payload.get('reason') or '').strip()
    if not isinstance(expected,int) or expected<1 or not actor or not reason:raise ValueError('expected_version, actor_id e reason obrigatórios')
    tenant_id=current_tenant_id(required=False);normalized=normalize_route_geometry(payload.get('geometry'),payload.get('corridor_meters'));conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.routes WHERE public_id=%s AND (%s IS NULL OR tenant_id=%s) FOR UPDATE",(public_id,tenant_id,tenant_id));route=cursor.fetchone()
        if not route:raise LookupError('Rota não encontrada')
        if route['version']!=expected:raise RouteConflict('Versão divergente')
        new_version=expected+1;name=str(payload.get('name') or route['name']).strip()
        cursor.execute("UPDATE monitoramento.routes SET name=%s,description=%s,version=%s WHERE id=%s AND version=%s",(name,payload.get('description',route['description']),new_version,route['id'],expected))
        cursor.execute("""INSERT INTO monitoramento.route_versions(route_id,version_no,geometry_json,geometry_sha256,corridor_meters,length_meters,created_by,change_reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",(route['id'],new_version,normalized['geometry_json'],normalized['geometry_sha256'],normalized['corridor_meters'],normalized['length_meters'],actor,reason))
        cursor.execute("INSERT INTO monitoramento.route_audit_log(route_id,event_type,actor_id,reason,snapshot_json) VALUES(%s,'version_created',%s,%s,%s)",(route['id'],actor,reason,json.dumps({'version':new_version,'geometry_sha256':normalized['geometry_sha256']})))
        conn.commit();return get_route(public_id)
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()

def archive_route(public_id,expected_version,actor_id,reason):
    if not isinstance(expected_version,int) or expected_version<1 or not str(actor_id or '').strip() or not str(reason or '').strip():
        raise ValueError('expected_version, actor_id e reason obrigatórios')
    tenant_id=current_tenant_id(required=False);conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.routes WHERE public_id=%s AND (%s IS NULL OR tenant_id=%s) FOR UPDATE",(public_id,tenant_id,tenant_id));route=cursor.fetchone()
        if not route:raise LookupError('Rota não encontrada')
        if route['version']!=expected_version:raise RouteConflict('Versão divergente')
        cursor.execute("UPDATE monitoramento.routes SET status='archived' WHERE id=%s AND version=%s",(route['id'],expected_version));cursor.execute("INSERT INTO monitoramento.route_audit_log(route_id,event_type,actor_id,reason,snapshot_json) VALUES(%s,'archived',%s,%s,'{\"status\":\"archived\"}')",(route['id'],actor_id,reason));conn.commit();return {'public_id':public_id,'status':'archived','version':expected_version}
    except Exception:conn.rollback();raise
    finally:cursor.close();conn.close()
