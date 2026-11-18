from pathlib import Path
import re

import pytest

from server.agent_read_tools import ToolDenied,ToolScope
from server.agent_tool_policy import ToolPermission,ToolPolicySet,validate_constraints


MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'036_create_agent_tool_policies.sql'


def permission(**overrides):
    value={'policy_id':1,'tool_name':'position.history','allowed_arguments':('vehicle_id','limit'),'allowed_sources':('tracker',),'max_limit':20}
    value.update(overrides);return ToolPermission(**value)


def test_allowlist_authorizes_only_declared_tool_arguments_sources_and_limit():
    policies=ToolPolicySet(7,{'position.history':permission()})
    assert policies.authorize('position.history',{'vehicle_id':1,'limit':20},ToolScope((1,),('tracker',),20)).policy_id==1
    with pytest.raises(ToolDenied,match='allowlist'):policies.authorize('vehicle.get',{'vehicle_id':1},ToolScope((1,),('tracker',),20))
    with pytest.raises(ToolDenied,match='Parâmetros'):policies.authorize('position.history',{'vehicle_id':1,'url':'x'},ToolScope((1,),('tracker',),20))
    with pytest.raises(ToolDenied,match='Fonte'):policies.authorize('position.history',{'vehicle_id':1},ToolScope((1,),('dirijabem',),20))
    with pytest.raises(ToolDenied,match='limit'):policies.authorize('position.history',{'vehicle_id':1,'limit':21},ToolScope((1,),('tracker',),20))


def test_omitted_limit_is_evaluated_as_the_effective_history_limit():
    policies=ToolPolicySet(7,{'position.history':permission(max_limit=5)})
    with pytest.raises(ToolDenied,match='limit'):
        policies.authorize('position.history',{'vehicle_id':1},ToolScope((1,),('tracker',),20))


def test_constraints_are_exact_and_canonical():
    result=validate_constraints('vehicle.get',{'allowed_arguments':['vehicle_id'],'allowed_sources':['tracker'],'max_limit':1})
    assert result=={'allowed_arguments':['vehicle_id'],'allowed_sources':['tracker'],'max_limit':1}
    with pytest.raises(ValueError):validate_constraints('sql.query',{'allowed_arguments':['vehicle_id'],'allowed_sources':['tracker'],'max_limit':1})
    with pytest.raises(ValueError):validate_constraints('vehicle.get',{'allowed_arguments':['vehicle_id'],'allowed_sources':['tracker'],'max_limit':1,'extra':True})


def test_migration_versions_policy_by_config_and_makes_it_immutable():
    sql=MIGRATION.read_text(encoding='utf-8').lower()
    assert 'agent_tool_policies' in sql and 'config_version_id' in sql
    assert 'uq_agent_tool_policy' in sql and 'json_valid(constraints_json)' in sql
    assert 'trg_agent_tool_policy_immutable_update' in sql
    assert 'trg_agent_tool_policy_immutable_delete' in sql
    assert re.search(r'\bdelete\s+from\b',sql) is None and 'drop table' not in sql
