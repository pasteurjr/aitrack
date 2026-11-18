"""Ferramentas fechadas de leitura; não aceita SQL, URL ou operação arbitrária."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import time
from typing import Dict, Iterable, Optional

from .geofence_db import GEOFENCE_SELECT, _serialize as serialize_geofence
from .monitor_db import get_connection


TOOL_NAMES = {
    'vehicle.get', 'position.latest', 'position.history', 'geofence.list_for_vehicle',
}


class ToolDenied(ValueError):
    code = 'AGENT_TOOL_DENIED'


@dataclass(frozen=True)
class ToolScope:
    vehicle_ids: tuple[int, ...]
    source_codes: tuple[str, ...] = ('tracker', 'dirijabem')
    max_history_points: int = 100

    def validate(self):
        if not self.vehicle_ids or any(not isinstance(item, int) or item < 1 for item in self.vehicle_ids):
            raise ToolDenied('Escopo exige vehicle_ids canônicos')
        if not set(self.source_codes) <= {'tracker', 'dirijabem'}:
            raise ToolDenied('Escopo contém fonte não permitida')
        if not 1 <= self.max_history_points <= 500:
            raise ToolDenied('max_history_points deve estar entre 1 e 500')


def _json(value):
    def default(item):
        if isinstance(item, datetime): return item.isoformat()
        if isinstance(item, Decimal): return float(item)
        raise TypeError(type(item).__name__)
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True, default=default)


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


class VehicleReadRepository:
    def get_vehicle(self, vehicle_id: int):
        conn=get_connection(); cursor=conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id,public_id,placa,descricao,ativo,version,criado_em,atualizado_em "
                "FROM monitoramento.veiculos WHERE id=%s AND merged_into_id IS NULL",
                (vehicle_id,),
            )
            vehicle=cursor.fetchone()
            if not vehicle: return None
            cursor.execute(
                "SELECT fonte_codigo,tipo_identidade,valor_externo,principal,ultimo_visto_em "
                "FROM monitoramento.veiculo_identidades WHERE vehicle_id=%s AND ativo=TRUE "
                "ORDER BY fonte_codigo,principal DESC,id",
                (vehicle_id,),
            )
            vehicle['identities']=cursor.fetchall()
            return json.loads(_json(vehicle))
        finally: cursor.close();conn.close()

    def positions(self, vehicle_id: int, sources: Iterable[str], limit: int):
        conn=get_connection(); cursor=conn.cursor(dictionary=True); rows=[]
        try:
            if 'tracker' in sources:
                cursor.execute(
                    "SELECT CAST(valor_externo AS UNSIGNED) legacy_id FROM "
                    "monitoramento.veiculo_identidades WHERE vehicle_id=%s "
                    "AND fonte_codigo='tracker' AND tipo_identidade='vehicle_id' "
                    "AND ativo=TRUE ORDER BY principal DESC,id LIMIT 1",
                    (vehicle_id,),
                )
                identity=cursor.fetchone()
                if identity:
                    cursor.execute(
                        "SELECT 'tracker' source,CAST(LOCCOD AS CHAR) position_id,"
                        "ST_Y(LOCLATLONG) latitude,ST_X(LOCLATLONG) longitude,"
                        "VELATU speed,DATAHORA observed_at FROM tracker.localizacao "
                        "WHERE FK_VEICOD=%s ORDER BY LOCCOD DESC LIMIT %s",
                        (identity['legacy_id'], limit),
                    )
                    rows.extend(cursor.fetchall())
            if 'dirijabem' in sources:
                cursor.execute(
                    "SELECT CAST(mi.valor_externo AS UNSIGNED) user_id FROM "
                    "monitoramento.veiculo_motorista_vinculos vmv "
                    "JOIN monitoramento.motorista_identidades mi ON mi.driver_id=vmv.driver_id "
                    "AND mi.fonte_codigo='dirijabem' AND mi.tipo_identidade='user_id' AND mi.ativo=TRUE "
                    "WHERE vmv.vehicle_id=%s AND (vmv.valido_ate IS NULL OR vmv.valido_ate>=NOW()) "
                    "ORDER BY vmv.valido_desde DESC,vmv.id DESC LIMIT 1",
                    (vehicle_id,),
                )
                identity=cursor.fetchone()
                if identity:
                    cursor.execute(
                        "SELECT CODVIA FROM dirijabem.viagem WHERE CODUSU=%s "
                        "ORDER BY CODVIA DESC LIMIT 20",
                        (identity['user_id'],),
                    )
                    trip_ids=[row['CODVIA'] for row in cursor.fetchall()]
                else:
                    trip_ids=[]
                if trip_ids:
                    placeholders=','.join(['%s']*len(trip_ids))
                    cursor.execute(
                        "SELECT 'dirijabem' source,CAST(l.LOCDADCOD AS CHAR) position_id,"
                        "ST_Y(l.coords) latitude,ST_X(l.coords) longitude,l.VELATU speed,"
                        "l.DATAHORA observed_at FROM dirijabem.localizacaodados l WHERE "
                        f"l.CODVIA IN ({placeholders}) AND l.coords IS NOT NULL "
                        "ORDER BY l.LOCDADCOD DESC LIMIT %s",
                        tuple(trip_ids+[limit]),
                    )
                    rows.extend(cursor.fetchall())
            rows.sort(key=lambda row: row['observed_at'], reverse=True)
            return json.loads(_json(rows[:limit]))
        finally: cursor.close();conn.close()

    def geofences(self, vehicle_id: int, limit: int):
        conn=get_connection(); cursor=conn.cursor(dictionary=True)
        try:
            cursor.execute(
                GEOFENCE_SELECT +
                " WHERE g.status<>'archived' AND EXISTS (SELECT 1 FROM "
                "monitoramento.geofence_assignments ga WHERE ga.geofence_id=g.id "
                "AND ga.ativo=TRUE AND ga.target_type='vehicle' AND ga.vehicle_id=%s) "
                "ORDER BY g.atualizado_em DESC,g.id DESC LIMIT %s",
                (vehicle_id, limit),
            )
            return [serialize_geofence(row) for row in cursor.fetchall()]
        finally: cursor.close();conn.close()


class AgentReadToolService:
    def __init__(self, repository=None, audit_writer=None,
                 clock=time.monotonic):
        self.repository=repository or VehicleReadRepository()
        self.audit_writer=audit_writer or self._write_audit
        self.clock=clock

    def invoke(self, tool_name: str, arguments: Dict, scope: ToolScope, *,
               agent_id: int, correlation_id: str, run_id: Optional[int] = None):
        started=self.clock()
        try:
            scope.validate()
            if tool_name not in TOOL_NAMES: raise ToolDenied(f'Ferramenta não permitida: {tool_name}')
            if not isinstance(arguments, dict): raise ToolDenied('arguments deve ser objeto')
            vehicle_id=arguments.get('vehicle_id')
            if set(arguments)-{'vehicle_id','limit'}: raise ToolDenied('Argumentos não permitidos')
            if vehicle_id not in scope.vehicle_ids: raise ToolDenied('Veículo fora do escopo')
            limit=arguments.get('limit', 1 if tool_name=='position.latest' else scope.max_history_points)
            if not isinstance(limit,int) or isinstance(limit,bool) or limit<1: raise ToolDenied('limit inválido')
            if tool_name in {'position.history','geofence.list_for_vehicle'} and limit>scope.max_history_points:
                raise ToolDenied('limit excede escopo')
            if tool_name=='vehicle.get': result=self.repository.get_vehicle(vehicle_id)
            elif tool_name=='position.latest':
                positions=self.repository.positions(vehicle_id,scope.source_codes,1);result=positions[0] if positions else None
            elif tool_name=='position.history': result=self.repository.positions(vehicle_id,scope.source_codes,limit)
            else: result=self.repository.geofences(vehicle_id,limit)
            latency=max(0,int((self.clock()-started)*1000))
            envelope={'schema_version':'agent-tool-result.v1','tool':tool_name,'data':result}
            self.audit_writer(agent_id,run_id,tool_name,arguments,asdict(scope),'succeeded',
                              {'has_data':result is not None,'items':len(result) if isinstance(result,list) else (1 if result else 0)},
                              correlation_id,latency,None,_hash(envelope))
            return envelope
        except ToolDenied as exc:
            latency=max(0,int((self.clock()-started)*1000))
            self.audit_writer(agent_id,run_id,tool_name,arguments,asdict(scope),'denied',None,
                              correlation_id,latency,exc.code,None)
            raise
        except Exception as exc:
            latency=max(0,int((self.clock()-started)*1000))
            self.audit_writer(agent_id,run_id,tool_name,arguments,asdict(scope),'failed',None,
                              correlation_id,latency,type(exc).__name__,None)
            raise

    @staticmethod
    def _write_audit(agent_id,run_id,tool_name,arguments,scope,status,summary,
                     correlation_id,latency,error_code,result_hash):
        conn=get_connection();cursor=conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO monitoramento.agent_tool_invocations "
                "(public_id,run_id,agent_id,tool_name,arguments_json,scope_json,status,"
                "result_summary_json,arguments_sha256,result_sha256,correlation_id,error_code,latency_ms) "
                "VALUES(UUID(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (run_id,agent_id,tool_name,_json(arguments),_json(scope),status,
                 _json(summary) if summary is not None else None,_hash(arguments),result_hash,
                 correlation_id,error_code,latency),
            );conn.commit()
        except Exception: conn.rollback();raise
        finally:cursor.close();conn.close()
