"""Persistência idempotente do detector de rota para execuções ativas."""
from datetime import datetime
import json
from .monitor_db import get_connection
from .route_detector import distance_to_route_m,evolve_route_state,is_planned_stop

def evaluate_execution_position(execution_id,longitude,latitude,speed_kmh,observed_at,accuracy_m,source,external_position_id,connection=None):
    owns=connection is None;conn=connection or get_connection();cursor=conn.cursor(dictionary=True)
    try:
        if owns:conn.start_transaction()
        cursor.execute("""SELECT e.id,e.status,e.route_version_id,v.geometry_json,v.corridor_meters
          FROM monitoramento.route_executions e JOIN monitoramento.route_versions v ON v.id=e.route_version_id
          WHERE e.id=%s FOR UPDATE""",(execution_id,));execution=cursor.fetchone()
        if not execution or execution['status']!='active':return None
        cursor.execute("SELECT id FROM monitoramento.route_position_receipts WHERE execution_id=%s AND source=%s AND external_position_id=%s",(execution_id,source,str(external_position_id)))
        if cursor.fetchone():return {'idempotent_replay':True}
        cursor.execute("INSERT INTO monitoramento.route_execution_states(execution_id) VALUES(%s) ON DUPLICATE KEY UPDATE execution_id=execution_id",(execution_id,))
        cursor.execute("SELECT * FROM monitoramento.route_execution_states WHERE execution_id=%s FOR UPDATE",(execution_id,));state=cursor.fetchone()
        if state['last_observed_at'] and observed_at<=state['last_observed_at']:return {'ignored':'out_of_order'}
        geometry=json.loads(execution['geometry_json']);distance=distance_to_route_m([longitude,latitude],geometry['coordinates'])
        evolution=evolve_route_state(state['stable_on_route'],state['pending_on_route'],state['pending_samples'],distance,float(execution['corridor_meters']),accuracy_m)
        cursor.execute("SELECT longitude,latitude,radius_meters FROM monitoramento.route_planned_stops WHERE route_version_id=%s",(execution['route_version_id'],));planned=is_planned_stop([longitude,latitude],cursor.fetchall())
        stop_started=state['stop_started_at'];stop_event=None
        if float(speed_kmh or 0)<=2 and not planned:stop_started=stop_started or observed_at
        else:
            if stop_started and (observed_at-stop_started).total_seconds()>=300:stop_event='recover_stop'
            stop_started=None
        if stop_started and (observed_at-stop_started).total_seconds()>=300:stop_event='unplanned_stop'
        if evolution.transition=='deviation':
            cursor.execute("INSERT IGNORE INTO monitoramento.route_episodes(public_id,execution_id,episode_type,status,started_at,max_distance_meters,evidence_json) VALUES(UUID(),%s,'deviation','active',%s,%s,%s)",(execution_id,observed_at,distance,json.dumps({'source':source,'external_position_id':str(external_position_id)})))
        elif evolution.transition=='recovered':cursor.execute("UPDATE monitoramento.route_episodes SET status='recovered',ended_at=%s WHERE execution_id=%s AND episode_type='deviation' AND status='active'",(observed_at,execution_id))
        if stop_event=='unplanned_stop':cursor.execute("INSERT IGNORE INTO monitoramento.route_episodes(public_id,execution_id,episode_type,status,started_at,evidence_json) VALUES(UUID(),%s,'unplanned_stop','active',%s,%s)",(execution_id,stop_started,json.dumps({'source':source})))
        elif stop_event=='recover_stop':cursor.execute("UPDATE monitoramento.route_episodes SET status='recovered',ended_at=%s WHERE execution_id=%s AND episode_type='unplanned_stop' AND status='active'",(observed_at,execution_id))
        cursor.execute("""UPDATE monitoramento.route_execution_states SET stable_on_route=%s,pending_on_route=%s,pending_samples=%s,last_distance_meters=%s,last_observed_at=%s,stop_started_at=%s,last_speed_kmh=%s,version=version+1 WHERE execution_id=%s""",(evolution.stable_on_route,evolution.pending_on_route,evolution.pending_samples,distance,observed_at,stop_started,speed_kmh,execution_id))
        cursor.execute(
            """INSERT INTO monitoramento.route_position_receipts(
                 execution_id, source, external_position_id, observed_at,
                 longitude, latitude, speed_kmh, distance_meters
               ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                execution_id, source, str(external_position_id), observed_at,
                longitude, latitude, speed_kmh, distance,
            ),
        )
        if owns:conn.commit()
        return {'distance_meters':round(distance,2),'on_route':evolution.stable_on_route,'transition':evolution.transition,'stop_event':stop_event,'idempotent_replay':False}
    except Exception:
        if owns:conn.rollback()
        raise
    finally:cursor.close();owns and conn.close()

def evaluate_tracker_position(device_id,legacy_vehicle_id,**position):
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT vi.vehicle_id FROM monitoramento.veiculo_identidades vi WHERE vi.fonte_codigo='tracker' AND vi.ativo=TRUE AND ((vi.tipo_identidade='device_id' AND vi.valor_externo=%s) OR (vi.tipo_identidade='vehicle_id' AND vi.valor_externo=%s)) ORDER BY vi.principal DESC LIMIT 1""",(str(device_id or ''),str(legacy_vehicle_id)))
        identity=cursor.fetchone()
        if not identity:return []
        cursor.execute("""SELECT e.id FROM monitoramento.route_executions e JOIN monitoramento.route_assignments a ON a.id=e.assignment_id WHERE e.status='active' AND a.vehicle_id=%s""",(identity['vehicle_id'],));executions=cursor.fetchall()
    finally:cursor.close();conn.close()
    return [evaluate_execution_position(row['id'],source='tracker',**position) for row in executions]
