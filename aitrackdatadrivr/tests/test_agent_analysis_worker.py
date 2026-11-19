from pathlib import Path
from types import SimpleNamespace

from server.agent_analysis_worker import AgentAnalysisWorker,SEVERITY_PRIORITY
from server.agent_tool_policy import ToolPermission,ToolPolicySet


MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'038_create_agent_analysis_jobs.sql'


class Repo:
    def __init__(self,work=None):self.work=work;self.completed=[];self.failed=[]
    def claim(self,_worker):return {'id':3,'agent_id':2,'attempt_count':1,'idempotency_key':'incident:9','correlation_id':'corr-9'} if self.work else None
    def load_work(self,_id):return self.work
    def complete(self,*args):self.completed.append(args)
    def fail(self,*args):self.failed.append(args)
    def defer(self,*args):self.failed.append(args)


class Tools:
    def __init__(self):self.calls=[]
    def invoke(self,name,args,scope,**kwargs):self.calls.append((name,args,scope,kwargs));return {'data':{'tool':name}}


def work():
    return {'agent_id':2,'agent_key':'monitor-1','config_version_id':7,'instructions':'Analise evidências persistidas.',
            'provider_code':'test','model_code':'test-model','decision_policy':{'temperature':0},
            'limits':{'timeout_seconds':10,'max_context_events':20},'vehicle_id':9,'incident_id':9,
            'incident_type':'geofence_exit','severity':'high','incident_status':'open','context_snapshot':{'source':'tracker'}}


def decision():
    return {'schema_version':'vehicle-monitoring-decision.v1','classification':'attention','confidence':.8,
            'summary':'Incidente requer acompanhamento do operador.','risk':{'level':'medium','score':50,'rationale':'Evidência demanda confirmação.'},
            'evidence':[{'source':'tracker','type':'incident','ref':'incident:9','summary':'Incidente persistido.'}],
            'proposed_actions':[],'human_review':{'required':False,'reason':'Risco moderado e sem ação externa.','deadline_seconds':300}}


def test_worker_collects_allowed_context_calls_provider_and_completes(monkeypatch):
    repo=Repo(work());tools=Tools();captured={}
    permissions={'vehicle.get':ToolPermission(1,'vehicle.get',('vehicle_id',),('tracker','dirijabem'),1)}
    monkeypatch.setattr('server.agent_analysis_worker.load_tool_policy',lambda _id:ToolPolicySet(7,permissions))
    provider=SimpleNamespace(generate_decision=lambda request:(captured.update(request=request) or SimpleNamespace(provider_request_id='p1',fallback_used=False,fallback_reason=None,decision=decision(),input_tokens=10,output_tokens=20,cost_usd=.01)))
    create=lambda key,payload:(captured.update(key=key,payload=payload) or {'id':5,'public_id':'run-5','version':1})
    finish=lambda public,payload:(captured.update(public=public,finish=payload) or {'id':5})
    result=AgentAnalysisWorker('worker-1',repo,lambda _config:provider,tools,create,finish,clock=lambda:1).process_one()
    assert result=={'job_id':3,'run_id':5,'status':'completed'} and repo.completed==[(3,'worker-1',5)]
    assert [call[0] for call in tools.calls]==['vehicle.get']
    assert captured['payload']['incident_id']==9 and captured['finish']['decision']['confidence']==.8


def test_worker_requeues_explicit_failure_without_fabricating_decision(monkeypatch):
    repo=Repo(work());finished=[];monkeypatch.setattr('server.agent_analysis_worker.load_tool_policy',lambda _id:ToolPolicySet(7,{}))
    create=lambda *_args:{'id':5,'public_id':'run-5','version':1}
    finish=lambda public,payload:finished.append((public,payload))
    result=AgentAnalysisWorker(
        'worker-1',repo,
        lambda _config:(_ for _ in ()).throw(RuntimeError('provider missing')),
        Tools(),create,finish,
    ).process_one()
    assert result['status']=='failed' and result['error_code']=='RuntimeError'
    assert repo.completed==[] and repo.failed[0][0:3]==(3,'worker-1','RuntimeError')
    assert finished[0][1]['status']=='failed' and finished[0][1]['decision'] is None


def test_empty_queue_does_nothing():
    assert AgentAnalysisWorker('worker-1',Repo(),tool_service=Tools()).process_one() is None


def test_priority_mapping_and_migration_contract():
    assert SEVERITY_PRIORITY['critical']>SEVERITY_PRIORITY['high']>SEVERITY_PRIORITY['medium']>SEVERITY_PRIORITY['low']
    sql=MIGRATION.read_text(encoding='utf-8').lower()
    for token in ('agent_analysis_jobs','idempotency_key','priority','lease_expires_at','attempt_count','max_attempts','uq_agent_analysis_job_idempotency'):
        assert token in sql
    assert 'delete from' not in sql and 'drop table' not in sql
