from pathlib import Path
import re

from flask import Flask
import pytest

from server import agent_run_api, agent_run_db


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '033_create_agent_execution_ledger.sql'


def client():
    app = Flask(__name__); app.register_blueprint(agent_run_api.agent_run_bp)
    return app.test_client()


def test_migration_persists_version_context_metrics_errors_decision_and_correlation():
    sql = MIGRATION.read_text(encoding='utf-8').lower()
    for token in (
        'config_version_id', 'input_json', 'context_json', 'output_json', 'latency_ms',
        'cost_usd', 'error_code', 'correlation_id', 'agent_run_decisions',
        'uq_agent_run_idempotency', 'trg_agent_run_identity_immutable',
    ):
        assert token in sql
    assert sql.count('on delete restrict') >= 5
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


@pytest.mark.parametrize('target', ['failed', 'timed_out', 'cancelled'])
def test_completion_accepts_explicit_terminal_failures(target):
    error = 'provider_error' if target != 'cancelled' else None
    assert agent_run_db.plan_completion('running', target, None, error)['to_status'] == target


def test_success_requires_decision_and_only_running_can_finish():
    assert agent_run_db.plan_completion('running', 'succeeded', {'risk': 'high'}, None)['final']
    with pytest.raises(agent_run_db.AgentRunError, match='decisão'):
        agent_run_db.plan_completion('running', 'succeeded', {}, None)
    with pytest.raises(agent_run_db.AgentRunConflict):
        agent_run_db.plan_completion('succeeded', 'failed', None, 'x')


def test_failure_and_timeout_require_machine_readable_error():
    with pytest.raises(agent_run_db.AgentRunError, match='error_code'):
        agent_run_db.plan_completion('running', 'failed', None, None)
    with pytest.raises(agent_run_db.AgentRunError, match='error_code'):
        agent_run_db.plan_completion('running', 'timed_out', None, None)


def test_list_api_exposes_versioned_contract_and_filters(monkeypatch):
    monkeypatch.setattr(
        agent_run_api.agent_run_db, 'list_runs',
        lambda agent, status, correlation, limit: [{
            'agent_key': agent, 'status': status, 'correlation_id': correlation, 'limit': limit,
        }],
    )
    response = client().get(
        '/api/agent-runs?agent_key=monitor-1&status=succeeded&correlation_id=incident-9&limit=20'
    )
    assert response.status_code == 200
    assert response.get_json()['schema_version'] == 'agent-runs.v1'
    assert response.get_json()['runs'][0]['limit'] == 20


def test_list_api_rejects_non_numeric_limit_before_repository():
    response = client().get('/api/agent-runs?limit=x')
    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_AGENT_RUN_QUERY'
