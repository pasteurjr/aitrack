from pathlib import Path
import re

from flask import Flask
import pytest

from server import agent_config_api, agent_config_db


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '032_create_versioned_agent_config.sql'


def client():
    app = Flask(__name__)
    app.register_blueprint(agent_config_api.agent_config_bp)
    return app.test_client()


def payload(**overrides):
    value = {
        'agent_key': 'monitor-1',
        'objective': 'Proteger veículos e reduzir tempo de resposta.',
        'instructions': 'Analise somente evidências persistidas e explicite incerteza.',
        'provider_code': 'provider-configurable',
        'model_code': 'model-configurable',
        'decision_policy': {'require_evidence': True, 'human_on_critical': True},
        'limits': {
            'timeout_seconds': 30,
            'max_context_events': 100,
            'max_actions_per_run': 0,
        },
        'created_by': 'tester',
        'change_reason': 'Configuração inicial validada',
    }
    value.update(overrides)
    return value


def test_migration_models_identity_immutable_versions_hash_and_audit_safely():
    sql = MIGRATION.read_text(encoding='utf-8').lower()
    assert 'monitoramento.agent_definitions' in sql
    assert 'monitoramento.agent_config_versions' in sql
    assert 'monitoramento.agent_config_audit' in sql
    assert 'unique key uq_agent_config_version' in sql
    assert 'unique key uq_agent_config_active' in sql
    assert 'content_sha256 char(64)' in sql
    assert 'trg_agent_config_immutable_update' in sql
    assert 'trg_agent_config_immutable_delete' in sql
    assert "signal sqlstate '45000'" in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


def test_validation_canonicalizes_content_and_hash_is_repeatable():
    first = agent_config_db._validate(payload())
    second = agent_config_db._validate(payload(
        decision_policy={'human_on_critical': True, 'require_evidence': True},
    ))
    assert first['content_sha256'] == second['content_sha256']
    assert first['decision_policy_json'] == second['decision_policy_json']


def test_activation_readiness_requires_supported_provider_policy_and_action_capacity():
    config={'provider_code':'openai','limits_json':'{"max_actions_per_run":1}'}
    assert agent_config_db.validate_activation_readiness(config,{'autonomy_level':'execute'})
    with pytest.raises(ValueError,match='Provedor'):
        agent_config_db.validate_activation_readiness({**config,'provider_code':'unknown'},{'autonomy_level':'observe'})
    with pytest.raises(ValueError,match='política'):
        agent_config_db.validate_activation_readiness(config,None)
    with pytest.raises(ValueError,match='maior que zero'):
        agent_config_db.validate_activation_readiness(
            {'provider_code':'anthropic','limits_json':'{"max_actions_per_run":0}'},
            {'autonomy_level':'execute'},
        )


@pytest.mark.parametrize(
    ('change', 'match'),
    [
        ({'objective': 'curto'}, 'objective'),
        ({'instructions': 'curto'}, 'instructions'),
        ({'decision_policy': {}}, 'decision_policy'),
        ({'limits': {'timeout_seconds': 0, 'max_context_events': 1, 'max_actions_per_run': 0}}, 'timeout'),
        ({'limits': {'timeout_seconds': 30, 'max_context_events': 501, 'max_actions_per_run': 0}}, 'context'),
        ({'limits': {'timeout_seconds': 30, 'max_context_events': 1, 'max_actions_per_run': 21}}, 'actions'),
    ],
)
def test_validation_rejects_incomplete_or_unsafe_configuration(change, match):
    with pytest.raises(ValueError, match=match):
        agent_config_db._validate(payload(**change))


def test_list_api_exposes_versioned_contract(monkeypatch):
    monkeypatch.setattr(
        agent_config_api.agent_config_db,
        'list_configurations',
        lambda agent_key, status: [{'agent_key': agent_key, 'status': status}],
    )
    response = client().get('/api/agent-configurations?agent_key=monitor-1&status=active')
    assert response.status_code == 200
    assert response.get_json() == {
        'schema_version': 'agent-configurations.v1',
        'count': 1,
        'configurations': [{'agent_key': 'monitor-1', 'status': 'active'}],
    }


def test_create_api_maps_validation_not_found_and_success(monkeypatch):
    monkeypatch.setattr(
        agent_config_api.agent_config_db, 'create_configuration',
        lambda _body: (_ for _ in ()).throw(ValueError('limits inválido')),
    )
    assert client().post('/api/agent-configurations', json={}).status_code == 400

    monkeypatch.setattr(
        agent_config_api.agent_config_db, 'create_configuration',
        lambda _body: (_ for _ in ()).throw(LookupError('Agente não encontrado')),
    )
    assert client().post('/api/agent-configurations', json=payload()).status_code == 404

    monkeypatch.setattr(
        agent_config_api.agent_config_db, 'create_configuration',
        lambda body: {'id': 7, 'agent_key': body['agent_key'], 'version_number': 1},
    )
    created = client().post('/api/agent-configurations', json=payload())
    assert created.status_code == 201
    assert created.get_json()['version_number'] == 1


def test_activate_api_maps_not_found_invalid_and_success(monkeypatch):
    monkeypatch.setattr(
        agent_config_api.agent_config_db, 'activate_configuration',
        lambda *_args: (_ for _ in ()).throw(LookupError('Configuração não encontrada')),
    )
    assert client().post('/api/agent-configurations/99/activate', json={}).status_code == 404

    monkeypatch.setattr(
        agent_config_api.agent_config_db, 'activate_configuration',
        lambda config_id, *_args: {'id': config_id, 'status': 'active'},
    )
    response = client().post(
        '/api/agent-configurations/7/activate',
        json={'actor': 'tester', 'reason': 'Ativar versão validada'},
    )
    assert response.status_code == 200
    assert response.get_json()['status'] == 'active'


def test_catalog_and_policy_endpoints_are_typed(monkeypatch):
    monkeypatch.setattr(agent_config_db,'list_agents',lambda:[{'id':1,'agent_key':'monitor-1'}])
    response=client().get('/api/agent-configurations/agents')
    assert response.status_code==200 and response.get_json()['count']==1
    tools=client().get('/api/agent-configurations/tools').get_json()['tools']
    assert tools==sorted(tools) and 'vehicle.get' in tools
    monkeypatch.setattr(agent_config_api,'add_tool_policy',lambda config_id,*_args:config_id+10)
    created=client().post('/api/agent-configurations/7/tools',json={'tool_name':'vehicle.get','constraints':{},'actor':'x','reason':'reason'})
    assert created.status_code==201 and created.get_json()['id']==17
    monkeypatch.setattr(agent_config_api,'add_autonomy_policy',lambda config_id,*_args:config_id+20)
    created=client().post('/api/agent-configurations/7/autonomy',json={'policy':{},'actor':'x','reason':'reason'})
    assert created.status_code==201 and created.get_json()['id']==27
