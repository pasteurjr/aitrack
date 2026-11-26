from pathlib import Path
import re
import json

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


def test_trusted_safety_context_comes_from_persisted_run_input():
    assert agent_run_db._trusted_safety_context('{"severity":"critical","incident_type":"theft"}') == {'severity':'critical'}
    with pytest.raises(agent_run_db.AgentRunError, match='inválida'):
        agent_run_db._trusted_safety_context('{')
    with pytest.raises(agent_run_db.AgentRunError, match='objeto'):
        agent_run_db._trusted_safety_context('[]')


def test_finish_run_blocks_contact_when_model_understates_persisted_critical_incident(monkeypatch):
    from server.agent_autonomy import AutonomyPolicy, evaluate_autonomy
    from server.agent_decision_schema import SCHEMA_VERSION

    decision = {
        'schema_version': SCHEMA_VERSION, 'classification': 'attention', 'confidence': .9,
        'summary': 'O modelo classificou o sinal como risco baixo.',
        'risk': {'level': 'low', 'score': 10, 'rationale': 'Estimativa do modelo abaixo do risco real.'},
        'evidence': [{'source': 'tracker', 'type': 'speeding', 'ref': 'incident:critical-1',
                      'summary': 'Incidente crítico persistido no sistema.'}],
        'proposed_actions': [{'type': 'contact_owner', 'priority': 'normal',
                              'rationale': 'Confirmar situação com o responsável.',
                              'requires_approval': False}],
        'human_review': {'required': False, 'reason': 'O modelo não solicitou revisão.'},
    }

    class Cursor:
        def __init__(self, run):
            self.run = run; self.rowcount = 1; self.lastrowid = 51
            self.result = None; self.decision_row = None; self.queries = []
        def execute(self, sql, params=None):
            self.queries.append(sql)
            if 'SELECT * FROM monitoramento.agent_runs WHERE public_id' in sql:
                self.result = dict(self.run)
            elif sql.startswith('UPDATE monitoramento.agent_runs SET status'):
                self.run['status'], self.run['version'], self.run['output_json'] = params[:3]
                self.result = None
            elif 'INSERT INTO monitoramento.agent_run_decisions' in sql:
                self.decision_row = {
                    'id': self.lastrowid, 'format_version': params[1], 'decision_json': params[2],
                    'decision_sha256': params[3], 'autonomy_policy_id': params[4],
                    'autonomy_level': params[5], 'authorization_json': params[6],
                    'classification': 'attention', 'confidence': .9, 'risk_level': 'low',
                    'risk_score': 10, 'context_sha256': params[11],
                    'evidence_manifest_sha256': params[12], 'evidence_count': params[13],
                    'recorded_at': None,
                }
            elif 'SELECT * FROM monitoramento.agent_runs WHERE id' in sql:
                self.result = dict(self.run)
            elif 'SELECT id,format_version,decision_json' in sql:
                self.result = dict(self.decision_row)
            else:
                self.result = None
        def executemany(self, sql, params): self.queries.append(sql)
        def fetchone(self):
            result, self.result = self.result, None
            return result
        def fetchall(self): return []
        def close(self): pass

    class Connection:
        def __init__(self, run): self.fake_cursor = Cursor(run)
        def cursor(self, **_kwargs): return self.fake_cursor
        def start_transaction(self): pass
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass

    run = {
        'id': 8, 'public_id': 'run-test', 'config_version_id': 7, 'status': 'running',
        'version': 1, 'input_json': '{"severity":"critical","incident_type":"speeding"}',
        'context_json': '{}', 'output_json': None,
    }
    conn = Connection(run)
    monkeypatch.setattr(agent_run_db, 'get_connection', lambda: conn)
    policy = AutonomyPolicy(3, 7, 'execute', 'medium', ('contact_owner',), 'simulation')
    monkeypatch.setattr(
        agent_run_db, 'authorize_decision',
        lambda _version, value, safety_context=None: evaluate_autonomy(policy, value, safety_context),
    )
    result = agent_run_db.finish_run('run-test', {
        'status': 'succeeded', 'expected_version': 1, 'decision': decision,
        'output': {'fallback_used': False}, 'latency_ms': 5,
    })

    stored = json.loads(conn.fake_cursor.decision_row['authorization_json'])
    assert stored['trusted_incident_severity'] == 'critical'
    assert stored['actions'][0]['disposition'] == 'approval_required'
    assert stored['human_review_required'] is True
    assert not any('INSERT INTO monitoramento.agent_simulated_actions' in q for q in conn.fake_cursor.queries)
    assert result['status'] == 'succeeded'


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
