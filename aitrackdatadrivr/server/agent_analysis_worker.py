"""Worker idempotente: incidente -> contexto permitido -> decisão persistida."""

from dataclasses import asdict
from datetime import datetime
import json
import threading
import time
from typing import Callable, Dict, Optional

from .agent_read_tools import AgentReadToolService, ToolScope
from .agent_run_db import create_run, finish_run
from .agent_tool_policy import load_tool_policy
from .ai_provider import DecisionRequest, create_provider
from .ai_resilience import (
    CircuitBreaker, ResilientDecisionProvider, SafeHumanFallbackProvider,
)
from .monitor_db import get_connection


SEVERITY_PRIORITY = {'critical': 100, 'high': 80, 'medium': 50, 'low': 20}


class AnalysisJobConflict(RuntimeError):
    pass

class AgentPausedError(RuntimeError):
    code='AGENT_INCIDENT_NOT_ACTIVE'


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize(row):
    result = dict(row)
    for field in ('available_at','claimed_at','lease_expires_at','created_at','completed_at'):
        result[field] = _iso(result.get(field))
    return result


class AnalysisJobRepository:
    def enqueue(self, agent_key: str, incident_id: int, severity: str,
                idempotency_key: str, correlation_id: str, max_attempts=5):
        priority = SEVERITY_PRIORITY.get(severity)
        if priority is None:
            raise ValueError('severity inválida')
        if not isinstance(incident_id, int) or isinstance(incident_id, bool) or incident_id < 1:
            raise ValueError('incident_id inválido')
        if not idempotency_key or len(idempotency_key) > 150 or not correlation_id:
            raise ValueError('idempotency_key e correlation_id são obrigatórios')
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 20:
            raise ValueError('max_attempts deve estar entre 1 e 20')
        conn=get_connection();cursor=conn.cursor(dictionary=True)
        try:
            conn.start_transaction();cursor.execute(
                "SELECT id FROM monitoramento.agent_definitions WHERE agent_key=%s "
                "AND lifecycle_status='active' FOR UPDATE",(agent_key,))
            agent=cursor.fetchone()
            if not agent: raise LookupError('Agente ativo não encontrado')
            cursor.execute(
                "SELECT * FROM monitoramento.agent_analysis_jobs WHERE agent_id=%s "
                "AND idempotency_key=%s FOR UPDATE",(agent['id'],idempotency_key))
            existing=cursor.fetchone()
            if existing: conn.commit();return _serialize(existing)
            cursor.execute(
                "INSERT INTO monitoramento.agent_analysis_jobs "
                "(public_id,agent_id,incident_id,priority,max_attempts,idempotency_key,correlation_id) "
                "VALUES(UUID(),%s,%s,%s,%s,%s,%s)",
                (agent['id'],incident_id,priority,max_attempts,idempotency_key,correlation_id))
            job_id=cursor.lastrowid;cursor.execute(
                "SELECT * FROM monitoramento.agent_analysis_jobs WHERE id=%s",(job_id,))
            row=cursor.fetchone();conn.commit();return _serialize(row)
        except Exception: conn.rollback();raise
        finally: cursor.close();conn.close()

    def claim(self, worker_id: str, lease_seconds=120):
        if not worker_id or not 10 <= lease_seconds <= 900:
            raise ValueError('worker_id e lease_seconds válidos são obrigatórios')
        conn=get_connection();cursor=conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT GET_LOCK('monitoramento.agent_analysis_jobs.claim',2) acquired")
            if cursor.fetchone()['acquired'] != 1:
                raise AnalysisJobConflict('Não foi possível obter lock da fila')
            conn.start_transaction()
            cursor.execute(
                "UPDATE monitoramento.agent_analysis_jobs SET status='dead',claimed_by=NULL,"
                "claimed_at=NULL,lease_expires_at=NULL,last_error_code='LEASE_EXPIRED' "
                "WHERE status='claimed' AND lease_expires_at<CURRENT_TIMESTAMP(6) "
                "AND attempt_count>=max_attempts")
            cursor.execute(
                "UPDATE monitoramento.agent_analysis_jobs SET status='pending',claimed_by=NULL,"
                "claimed_at=NULL,lease_expires_at=NULL WHERE status='claimed' "
                "AND lease_expires_at<CURRENT_TIMESTAMP(6) AND attempt_count<max_attempts")
            cursor.execute(
                "SELECT * FROM monitoramento.agent_analysis_jobs WHERE status='pending' "
                "AND available_at<=CURRENT_TIMESTAMP(6) ORDER BY priority DESC,created_at,id "
                "LIMIT 1 FOR UPDATE")
            row=cursor.fetchone()
            if not row: conn.commit();return None
            cursor.execute(
                "UPDATE monitoramento.agent_analysis_jobs SET status='claimed',"
                "attempt_count=attempt_count+1,claimed_by=%s,claimed_at=CURRENT_TIMESTAMP(6),"
                "lease_expires_at=TIMESTAMPADD(SECOND,%s,CURRENT_TIMESTAMP(6)) "
                "WHERE id=%s AND status='pending'",(worker_id,lease_seconds,row['id']))
            if cursor.rowcount != 1: raise AnalysisJobConflict('Job foi reclamado por outro worker')
            cursor.execute("SELECT * FROM monitoramento.agent_analysis_jobs WHERE id=%s",(row['id'],))
            claimed=cursor.fetchone();conn.commit();return _serialize(claimed)
        except Exception: conn.rollback();raise
        finally:
            try:
                cursor.execute("SELECT RELEASE_LOCK('monitoramento.agent_analysis_jobs.claim')")
                cursor.fetchone()
            except Exception:
                pass
            cursor.close();conn.close()

    def load_work(self, job_id: int):
        conn=get_connection();cursor=conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT j.*,a.agent_key,v.id config_version_id,v.instructions,v.provider_code,"
                "v.model_code,v.decision_policy_json,v.limits_json,i.vehicle_id,i.incident_type,"
                "i.severity,i.status incident_status,i.context_snapshot,"
                "COALESCE(c.control_state,'active') control_state FROM "
                "monitoramento.agent_analysis_jobs j JOIN monitoramento.agent_definitions a "
                "ON a.id=j.agent_id JOIN monitoramento.agent_config_versions v "
                "ON v.agent_id=a.id AND v.status='active' JOIN monitoramento.incidents i "
                "ON i.id=j.incident_id LEFT JOIN monitoramento.agent_incident_controls c "
                "ON c.incident_id=i.id WHERE j.id=%s AND j.status='claimed'",(job_id,))
            row=cursor.fetchone()
            if not row: raise LookupError('Job reclamado/configuração ativa não encontrado')
            if row['control_state']!='active':raise AgentPausedError(f'Controle do incidente está {row["control_state"]}')
            row['decision_policy']=json.loads(row.pop('decision_policy_json'))
            row['limits']=json.loads(row.pop('limits_json'))
            if isinstance(row.get('context_snapshot'),str):
                row['context_snapshot']=json.loads(row['context_snapshot'])
            return row
        finally: cursor.close();conn.close()

    def complete(self, job_id: int, worker_id: str, run_id: int):
        return self._finish(job_id,worker_id,"status='completed',run_id=%s,completed_at=CURRENT_TIMESTAMP(6)",(run_id,))

    def defer(self,job_id,worker_id,error_code,message,retry_seconds=60):
        conn=get_connection();cursor=conn.cursor()
        try:
            cursor.execute("UPDATE monitoramento.agent_analysis_jobs SET status='pending',attempt_count=GREATEST(attempt_count-1,0),available_at=TIMESTAMPADD(SECOND,%s,CURRENT_TIMESTAMP(6)),claimed_by=NULL,claimed_at=NULL,lease_expires_at=NULL,last_error_code=%s,last_error_message=%s WHERE id=%s AND status='claimed' AND claimed_by=%s",(retry_seconds,error_code,str(message)[:1000],job_id,worker_id))
            if cursor.rowcount!=1:raise AnalysisJobConflict('Lease do job não pertence ao worker')
            conn.commit()
        except Exception:conn.rollback();raise
        finally:cursor.close();conn.close()

    def fail(self, job_id: int, worker_id: str, error_code: str, message: str, retry_seconds=30):
        conn=get_connection();cursor=conn.cursor(dictionary=True)
        try:
            conn.start_transaction();cursor.execute(
                "SELECT attempt_count,max_attempts FROM monitoramento.agent_analysis_jobs "
                "WHERE id=%s AND status='claimed' AND claimed_by=%s FOR UPDATE",(job_id,worker_id))
            row=cursor.fetchone()
            if not row: raise AnalysisJobConflict('Lease do job não pertence ao worker')
            dead=int(row['attempt_count'])>=int(row['max_attempts'])
            cursor.execute(
                "UPDATE monitoramento.agent_analysis_jobs SET status=%s,available_at="
                "TIMESTAMPADD(SECOND,%s,CURRENT_TIMESTAMP(6)),claimed_by=NULL,claimed_at=NULL,"
                "lease_expires_at=NULL,last_error_code=%s,last_error_message=%s WHERE id=%s",
                ('dead' if dead else 'pending',retry_seconds,str(error_code)[:100],str(message)[:1000],job_id))
            conn.commit();return 'dead' if dead else 'pending'
        except Exception:conn.rollback();raise
        finally:cursor.close();conn.close()

    def _finish(self,job_id,worker_id,set_sql,params):
        conn=get_connection();cursor=conn.cursor()
        try:
            cursor.execute(
                f"UPDATE monitoramento.agent_analysis_jobs SET {set_sql},claimed_by=NULL,"
                "claimed_at=NULL,lease_expires_at=NULL WHERE id=%s AND status='claimed' "
                "AND claimed_by=%s",tuple(params)+(job_id,worker_id))
            if cursor.rowcount!=1:raise AnalysisJobConflict('Lease do job não pertence ao worker')
            conn.commit();return True
        except Exception:conn.rollback();raise
        finally:cursor.close();conn.close()


_providers={};_providers_lock=threading.Lock()


def resilient_provider(config):
    key=config['provider_code']
    with _providers_lock:
        if key not in _providers:
            _providers[key]=ResilientDecisionProvider(
                create_provider(key),CircuitBreaker(),SafeHumanFallbackProvider())
        return _providers[key]


class AgentAnalysisWorker:
    def __init__(self,worker_id: str,repository=None,provider_factory=resilient_provider,
                 tool_service=None,run_creator=create_run,run_finisher=finish_run,
                 clock: Callable[[],float]=time.monotonic):
        self.worker_id=worker_id;self.repository=repository or AnalysisJobRepository()
        self.provider_factory=provider_factory;self.tool_service=tool_service or AgentReadToolService()
        self.run_creator=run_creator;self.run_finisher=run_finisher;self.clock=clock

    def process_one(self):
        job=self.repository.claim(self.worker_id)
        if not job:return None
        started=self.clock();run=None
        try:
            work=self.repository.load_work(job['id']);policy=load_tool_policy(work['config_version_id'])
            tool_context={}
            for name in sorted(policy.permissions):
                permission=policy.permissions[name]
                scope=ToolScope(
                    (work['vehicle_id'],),permission.allowed_sources,
                    min(100,work['limits']['max_context_events'],permission.max_limit),
                )
                args={'vehicle_id':work['vehicle_id']}
                if name in {'position.history','geofence.list_for_vehicle'}:args['limit']=scope.max_history_points
                tool_context[name]=self.tool_service.invoke(
                    name,args,scope,agent_id=work['agent_id'],
                    config_version_id=work['config_version_id'],correlation_id=job['correlation_id'])['data']
            input_value={'incident_id':work['incident_id'],'incident_type':work['incident_type'],
                         'severity':work['severity'],'status':work['incident_status']}
            context={'incident_snapshot':work['context_snapshot'],'tools':tool_context}
            run=self.run_creator(work['agent_key'],{
                'trigger_type':'event',
                'idempotency_key':f"{job['idempotency_key']}:attempt:{job['attempt_count']}",
                'correlation_id':job['correlation_id'],'incident_id':work['incident_id'],
                'vehicle_id':work['vehicle_id'],'attempt_number':job['attempt_count'],
                'input':input_value,'context':context})
            request=DecisionRequest(
                model=work['model_code'],instructions=work['instructions'],input=input_value,
                context=context,max_output_tokens=int(work['limits'].get('max_output_tokens',2000)),
                temperature=float(work['decision_policy'].get('temperature',0)),
                timeout_seconds=int(work['limits']['timeout_seconds']),
                correlation_id=job['correlation_id'])
            result=self.provider_factory(work).generate_decision(request)
            latency=max(0,int((self.clock()-started)*1000))
            finished=self.run_finisher(run['public_id'],{
                'status':'succeeded','expected_version':run['version'],
                'output':{'provider_request_id':result.provider_request_id,
                          'fallback_used':result.fallback_used,
                          'fallback_reason':result.fallback_reason},
                'decision':result.decision,'latency_ms':latency,
                'input_tokens':result.input_tokens,'output_tokens':result.output_tokens,
                'cost_usd':result.cost_usd})
            self.repository.complete(job['id'],self.worker_id,finished['id'])
            return {'job_id':job['id'],'run_id':finished['id'],'status':'completed'}
        except Exception as exc:
            code=getattr(exc,'code',type(exc).__name__)
            if isinstance(exc,AgentPausedError):
                self.repository.defer(job['id'],self.worker_id,code,str(exc));return {'job_id':job['id'],'run_id':None,'status':'deferred','error_code':code}
            if run:
                try:
                    self.run_finisher(run['public_id'],{
                        'status':'failed','expected_version':run['version'],
                        'output':None,'decision':None,'error_code':code,
                        'error_message':str(exc)[:1000],
                        'latency_ms':max(0,int((self.clock()-started)*1000)),
                    })
                except Exception:
                    pass
            self.repository.fail(job['id'],self.worker_id,code,str(exc))
            return {'job_id':job['id'],'run_id':run and run.get('id'),'status':'failed','error_code':code}
