from pathlib import Path
import re

import pytest

from server.agent_read_tools import AgentReadToolService, ToolDenied, ToolScope, TOOL_NAMES


MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'035_create_agent_tool_audit.sql'


class Repository:
    def __init__(self): self.calls=[]
    def get_vehicle(self,vehicle_id): self.calls.append(('vehicle',vehicle_id));return {'id':vehicle_id}
    def positions(self,vehicle_id,sources,limit): self.calls.append(('positions',vehicle_id,tuple(sources),limit));return [{'source':'tracker','position_id':'1'}]
    def geofences(self,vehicle_id,limit): self.calls.append(('geofences',vehicle_id,limit));return [{'id':9}]


def service():
    repository=Repository();audits=[]
    return AgentReadToolService(repository,lambda *args:audits.append(args),clock=lambda:1.0),repository,audits


def test_registry_contains_only_four_read_tools():
    assert TOOL_NAMES=={'vehicle.get','position.latest','position.history','geofence.list_for_vehicle'}
    assert all(not name.startswith(('create','update','delete','send','command')) for name in TOOL_NAMES)


@pytest.mark.parametrize('tool',sorted(TOOL_NAMES))
def test_allowed_tools_return_versioned_result_and_audit(tool):
    instance,repository,audits=service();scope=ToolScope((1,),('tracker',),20)
    result=instance.invoke(tool,{'vehicle_id':1,'limit':5},scope,agent_id=2,correlation_id='c1')
    assert result['schema_version']=='agent-tool-result.v1' and result['tool']==tool
    assert len(repository.calls)==1 and audits[0][5]=='succeeded'


@pytest.mark.parametrize(
    ('tool','arguments','scope','match'),[
        ('sql.query',{'vehicle_id':1},ToolScope((1,)),'não permitida'),
        ('vehicle.get',{'vehicle_id':2},ToolScope((1,)),'fora do escopo'),
        ('position.history',{'vehicle_id':1,'limit':21},ToolScope((1,),max_history_points=20),'excede'),
        ('position.latest',{'vehicle_id':1,'url':'http://x'},ToolScope((1,)),'Argumentos'),
    ],
)
def test_denies_unknown_out_of_scope_excessive_or_extra_arguments(tool,arguments,scope,match):
    instance,repository,audits=service()
    with pytest.raises(ToolDenied,match=match):instance.invoke(tool,arguments,scope,agent_id=2,correlation_id='c')
    assert repository.calls==[] and audits[0][5]=='denied'


def test_repository_failure_is_audited_and_propagated():
    instance,repository,audits=service()
    repository.get_vehicle=lambda _id:(_ for _ in ()).throw(RuntimeError('db'))
    with pytest.raises(RuntimeError):instance.invoke('vehicle.get',{'vehicle_id':1},ToolScope((1,)),agent_id=2,correlation_id='c')
    assert audits[0][5]=='failed' and audits[0][9]=='RuntimeError'


def test_scope_rejects_unknown_sources_and_unbounded_history():
    with pytest.raises(ToolDenied):ToolScope((1,),('tracker','internet'),10).validate()
    with pytest.raises(ToolDenied):ToolScope((1,),max_history_points=501).validate()


def test_migration_audits_scope_hash_result_latency_and_correlation_safely():
    sql=MIGRATION.read_text(encoding='utf-8').lower()
    for token in ('agent_tool_invocations','scope_json','arguments_sha256','result_sha256','latency_ms','correlation_id'):
        assert token in sql
    assert re.search(r'\bdelete\s+from\b',sql) is None and 'drop table' not in sql
