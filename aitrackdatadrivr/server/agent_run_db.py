"""Ledger idempotente de execução; não contém integração com provedor externo."""

import json
from datetime import datetime
from typing import Dict, Optional

from .monitor_db import get_connection


FINAL_STATUSES = {'succeeded', 'failed', 'timed_out', 'cancelled'}
TRIGGER_TYPES = {'scheduled', 'event', 'manual', 'retry'}


class AgentRunError(ValueError):
    pass


class AgentRunConflict(AgentRunError):
    pass


def plan_completion(status: str, target: str, decision: Optional[Dict],
                    error_code: Optional[str]) -> Dict:
    if status != 'running':
        raise AgentRunConflict(f'Execução em estado {status} não pode ser finalizada')
    if target not in FINAL_STATUSES:
        raise AgentRunError('Estado final inválido')
    if target == 'succeeded' and (not isinstance(decision, dict) or not decision):
        raise AgentRunError('Sucesso exige decisão não vazia')
    if target in {'failed', 'timed_out'} and not error_code:
        raise AgentRunError('Falha/timeout exige error_code')
    return {'from_status': status, 'to_status': target, 'final': True}


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize(row: Dict, decision=None) -> Dict:
    result = dict(row)
    for source, target in (
        ('input_json', 'input'), ('context_json', 'context'), ('output_json', 'output'),
    ):
        raw = result.pop(source, None)
        result[target] = json.loads(raw) if raw else None
    for field in ('queued_at', 'started_at', 'completed_at'):
        result[field] = _iso(result.get(field))
    result['decision'] = decision
    return result


def _decision(cursor, run_id: int):
    cursor.execute(
        "SELECT format_version,decision_json,recorded_at FROM "
        "monitoramento.agent_run_decisions WHERE run_id=%s",
        (run_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        'format_version': row['format_version'],
        'value': json.loads(row['decision_json']),
        'recorded_at': _iso(row['recorded_at']),
    }


def list_runs(agent_key: Optional[str] = None, status: Optional[str] = None,
              correlation_id: Optional[str] = None, limit: int = 100):
    if status and status not in FINAL_STATUSES | {'queued', 'running'}:
        raise AgentRunError('status inválido')
    if not 1 <= limit <= 200:
        raise AgentRunError('limit deve estar entre 1 e 200')
    clauses, params = [], []
    if agent_key:
        clauses.append('a.agent_key=%s'); params.append(agent_key)
    if status:
        clauses.append('r.status=%s'); params.append(status)
    if correlation_id:
        clauses.append('r.correlation_id=%s'); params.append(correlation_id)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT r.*,a.agent_key,v.version_number config_version "
            "FROM monitoramento.agent_runs r "
            "JOIN monitoramento.agent_definitions a ON a.id=r.agent_id "
            "JOIN monitoramento.agent_config_versions v ON v.id=r.config_version_id" +
            where + " ORDER BY r.queued_at DESC,r.id DESC LIMIT %s",
            tuple(params + [limit]),
        )
        rows = cursor.fetchall()
        return [_serialize(row, _decision(cursor, row['id'])) for row in rows]
    finally:
        cursor.close(); conn.close()


def create_run(agent_key: str, payload: Dict) -> Dict:
    agent_key = str(agent_key or '').strip().lower()
    trigger = str(payload.get('trigger_type') or '').strip().lower()
    idempotency = str(payload.get('idempotency_key') or '').strip()
    correlation = str(payload.get('correlation_id') or '').strip()
    input_value, context = payload.get('input'), payload.get('context')
    attempt = payload.get('attempt_number', 1)
    if not agent_key or trigger not in TRIGGER_TYPES:
        raise AgentRunError('agent_key e trigger_type válido são obrigatórios')
    if not idempotency or not correlation:
        raise AgentRunError('idempotency_key e correlation_id são obrigatórios')
    if not isinstance(input_value, dict) or not isinstance(context, dict):
        raise AgentRunError('input e context devem ser objetos JSON')
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 20:
        raise AgentRunError('attempt_number deve estar entre 1 e 20')

    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT a.id agent_id,v.id config_id,v.provider_code,v.model_code "
            "FROM monitoramento.agent_definitions a "
            "JOIN monitoramento.agent_config_versions v ON v.agent_id=a.id "
            "WHERE a.agent_key=%s AND a.lifecycle_status='active' "
            "AND v.status='active' FOR UPDATE",
            (agent_key,),
        )
        config = cursor.fetchone()
        if not config:
            raise LookupError('Agente não possui configuração ativa')
        cursor.execute(
            "SELECT * FROM monitoramento.agent_runs WHERE agent_id=%s "
            "AND idempotency_key=%s FOR UPDATE",
            (config['agent_id'], idempotency),
        )
        existing = cursor.fetchone()
        if existing:
            conn.commit()
            return _serialize(existing, _decision(cursor, existing['id']))
        cursor.execute(
            "INSERT INTO monitoramento.agent_runs "
            "(public_id,agent_id,config_version_id,incident_id,vehicle_id,trigger_type,"
            "status,attempt_number,idempotency_key,correlation_id,causation_id,provider_code,"
            "model_code,input_json,context_json) "
            "VALUES(UUID(),%s,%s,%s,%s,%s,'running',%s,%s,%s,%s,%s,%s,%s,%s)",
            (config['agent_id'], config['config_id'], payload.get('incident_id'),
             payload.get('vehicle_id'), trigger, attempt, idempotency, correlation,
             payload.get('causation_id'), config['provider_code'], config['model_code'],
             json.dumps(input_value), json.dumps(context)),
        )
        run_id = cursor.lastrowid
        cursor.execute(
            "UPDATE monitoramento.agent_runs SET started_at=CURRENT_TIMESTAMP(6) WHERE id=%s",
            (run_id,),
        )
        cursor.execute('SELECT * FROM monitoramento.agent_runs WHERE id=%s', (run_id,))
        row = cursor.fetchone(); conn.commit()
        return _serialize(row)
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()


def finish_run(public_id: str, payload: Dict) -> Dict:
    target = str(payload.get('status') or '').strip().lower()
    expected_version = payload.get('expected_version')
    output, decision = payload.get('output'), payload.get('decision')
    error_code = str(payload.get('error_code') or '').strip() or None
    if not isinstance(expected_version, int):
        raise AgentRunError('expected_version é obrigatório')
    for name in ('latency_ms', 'input_tokens', 'output_tokens'):
        value = payload.get(name)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise AgentRunError(f'{name} deve ser inteiro não negativo')
    cost = payload.get('cost_usd')
    if cost is not None and (not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0):
        raise AgentRunError('cost_usd deve ser não negativo')

    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.agent_runs WHERE public_id=%s FOR UPDATE",
            (public_id,),
        )
        run = cursor.fetchone()
        if not run:
            raise LookupError('Execução não encontrada')
        if int(run['version']) != expected_version:
            raise AgentRunConflict('Versão da execução foi alterada')
        plan_completion(run['status'], target, decision, error_code)
        cursor.execute(
            "UPDATE monitoramento.agent_runs SET status=%s,version=%s,output_json=%s,"
            "input_tokens=%s,output_tokens=%s,cost_usd=%s,latency_ms=%s,error_code=%s,"
            "error_message=%s,completed_at=CURRENT_TIMESTAMP(6) WHERE id=%s AND version=%s",
            (target, expected_version + 1, json.dumps(output) if output is not None else None,
             payload.get('input_tokens'), payload.get('output_tokens'), cost,
             payload.get('latency_ms'), error_code, payload.get('error_message'),
             run['id'], expected_version),
        )
        if target == 'succeeded':
            cursor.execute(
                "INSERT INTO monitoramento.agent_run_decisions "
                "(run_id,format_version,decision_json) VALUES(%s,%s,%s)",
                (run['id'], payload.get('format_version') or 'unstructured.v1',
                 json.dumps(decision)),
            )
        cursor.execute('SELECT * FROM monitoramento.agent_runs WHERE id=%s', (run['id'],))
        row = cursor.fetchone(); conn.commit()
        return _serialize(row, _decision(cursor, run['id']))
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()
