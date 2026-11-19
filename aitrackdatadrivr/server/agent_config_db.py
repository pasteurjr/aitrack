"""Configurações imutáveis e ativação auditável do runtime de agentes."""

import hashlib
import json
from datetime import datetime
from typing import Dict, Optional

from .monitor_db import get_connection


VALID_STATUSES = {'draft', 'active', 'superseded', 'retired'}
REQUIRED_LIMITS = {
    'timeout_seconds': (1, 300),
    'max_context_events': (1, 500),
    'max_actions_per_run': (0, 20),
}
SUPPORTED_PROVIDERS = {'anthropic','openai'}


def validate_activation_readiness(config: Dict, autonomy: Optional[Dict]):
    if config.get('provider_code') not in SUPPORTED_PROVIDERS:
        raise ValueError('Provedor não suportado para ativação')
    if not autonomy:
        raise ValueError('Configuração exige política de autonomia antes da ativação')
    limits=json.loads(config['limits_json']) if isinstance(config.get('limits_json'),str) else config.get('limits',{})
    if autonomy['autonomy_level']=='execute' and limits.get('max_actions_per_run',0)<1:
        raise ValueError('Autonomia execute exige max_actions_per_run maior que zero')
    return True


def _canonical(value: Dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _serialize(row: Dict) -> Dict:
    result = dict(row)
    result['decision_policy'] = json.loads(result.pop('decision_policy_json'))
    result['limits'] = json.loads(result.pop('limits_json'))
    for field in ('created_at', 'activated_at', 'superseded_at'):
        if isinstance(result.get(field), datetime):
            result[field] = result[field].isoformat()
    return result


def _validate(payload: Dict) -> Dict:
    agent_key = str(payload.get('agent_key') or '').strip().lower()
    objective = str(payload.get('objective') or '').strip()
    instructions = str(payload.get('instructions') or '').strip()
    provider = str(payload.get('provider_code') or '').strip().lower()
    model = str(payload.get('model_code') or '').strip()
    actor = str(payload.get('created_by') or '').strip()
    reason = str(payload.get('change_reason') or '').strip()
    policy, limits = payload.get('decision_policy'), payload.get('limits')
    if not agent_key or len(agent_key) > 100:
        raise ValueError('agent_key é obrigatório e deve ter até 100 caracteres')
    if len(objective) < 10 or len(instructions) < 20:
        raise ValueError('objective (mín. 10) e instructions (mín. 20) são obrigatórios')
    if not provider or not model:
        raise ValueError('provider_code e model_code são obrigatórios')
    if not isinstance(policy, dict) or not policy:
        raise ValueError('decision_policy deve ser objeto JSON não vazio')
    if not isinstance(limits, dict):
        raise ValueError('limits deve ser objeto JSON')
    for name, (minimum, maximum) in REQUIRED_LIMITS.items():
        value = limits.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ValueError(f'limits.{name} deve estar entre {minimum} e {maximum}')
    if not actor or len(reason) < 5:
        raise ValueError('created_by e change_reason (mín. 5) são obrigatórios')
    content = {
        'objective': objective,
        'instructions': instructions,
        'provider_code': provider,
        'model_code': model,
        'decision_policy': policy,
        'limits': limits,
    }
    return {
        'agent_key': agent_key,
        **content,
        'decision_policy_json': _canonical(policy),
        'limits_json': _canonical(limits),
        'content_sha256': hashlib.sha256(_canonical(content).encode('utf-8')).hexdigest(),
        'created_by': actor,
        'change_reason': reason,
    }


def list_configurations(agent_key: Optional[str] = None, status: Optional[str] = None):
    if status and status not in VALID_STATUSES:
        raise ValueError('status inválido')
    clauses, params = [], []
    if agent_key:
        clauses.append('a.agent_key=%s')
        params.append(agent_key)
    if status:
        clauses.append('v.status=%s')
        params.append(status)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT v.*,a.agent_key,a.display_name,a.monitor_id "
            "FROM monitoramento.agent_config_versions v "
            "JOIN monitoramento.agent_definitions a ON a.id=v.agent_id" + where +
            " ORDER BY a.agent_key,v.version_number DESC",
            tuple(params),
        )
        configurations=[_serialize(row) for row in cursor.fetchall()]
        ids=[item['id'] for item in configurations]
        if not ids:return configurations
        placeholders=','.join(['%s']*len(ids));by_id={item['id']:item for item in configurations}
        for item in configurations:
            item['tool_policies']=[];item['autonomy_policy']=None
        cursor.execute(
            "SELECT id,config_version_id,tool_name,constraints_json FROM "
            f"monitoramento.agent_tool_policies WHERE config_version_id IN ({placeholders}) "
            "ORDER BY config_version_id,tool_name",tuple(ids))
        for row in cursor.fetchall():
            by_id[row['config_version_id']]['tool_policies'].append({
                'id':row['id'],'tool_name':row['tool_name'],
                'constraints':json.loads(row['constraints_json']),
            })
        cursor.execute(
            "SELECT id,config_version_id,autonomy_level,execution_mode,max_autonomous_risk,"
            "allowed_autonomous_actions_json FROM monitoramento.agent_autonomy_policies "
            f"WHERE config_version_id IN ({placeholders})",tuple(ids))
        for row in cursor.fetchall():
            by_id[row['config_version_id']]['autonomy_policy']={
                'id':row['id'],'autonomy_level':row['autonomy_level'],
                'execution_mode':row['execution_mode'],
                'max_autonomous_risk':row['max_autonomous_risk'],
                'allowed_autonomous_actions':json.loads(row['allowed_autonomous_actions_json']),
            }
        return configurations
    finally:
        cursor.close()
        conn.close()


def list_agents():
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT a.id,a.agent_key,a.display_name,a.monitor_id,a.lifecycle_status,"
            "COUNT(v.id) version_count,MAX(CASE WHEN v.status='active' THEN v.id END) active_config_id "
            "FROM monitoramento.agent_definitions a LEFT JOIN "
            "monitoramento.agent_config_versions v ON v.agent_id=a.id "
            "GROUP BY a.id,a.agent_key,a.display_name,a.monitor_id,a.lifecycle_status "
            "ORDER BY a.display_name,a.id")
        return cursor.fetchall()
    finally:cursor.close();conn.close()


def create_configuration(payload: Dict) -> Dict:
    data = _validate(payload)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT id FROM monitoramento.agent_definitions "
            "WHERE agent_key=%s AND lifecycle_status='active' FOR UPDATE",
            (data['agent_key'],),
        )
        agent = cursor.fetchone()
        if not agent:
            raise LookupError('Agente ativo não encontrado')
        cursor.execute(
            "SELECT COALESCE(MAX(version_number),0) latest FROM "
            "monitoramento.agent_config_versions WHERE agent_id=%s FOR UPDATE",
            (agent['id'],),
        )
        version = int(cursor.fetchone()['latest']) + 1
        cursor.execute(
            "INSERT INTO monitoramento.agent_config_versions "
            "(agent_id,version_number,objective,instructions,provider_code,model_code,"
            "decision_policy_json,limits_json,content_sha256,created_by,change_reason) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (agent['id'], version, data['objective'], data['instructions'],
             data['provider_code'], data['model_code'], data['decision_policy_json'],
             data['limits_json'], data['content_sha256'], data['created_by'],
             data['change_reason']),
        )
        config_id = cursor.lastrowid
        cursor.execute(
            "SELECT v.*,a.agent_key,a.display_name,a.monitor_id "
            "FROM monitoramento.agent_config_versions v JOIN monitoramento.agent_definitions a "
            "ON a.id=v.agent_id WHERE v.id=%s",
            (config_id,),
        )
        row = cursor.fetchone()
        cursor.execute(
            "INSERT INTO monitoramento.agent_config_audit "
            "(config_version_id,event_type,actor,reason,snapshot_json,correlation_id) "
            "VALUES(%s,'created',%s,%s,%s,%s)",
            (config_id, data['created_by'], data['change_reason'], _canonical(_serialize(row)),
             payload.get('correlation_id')),
        )
        conn.commit()
        return _serialize(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def activate_configuration(config_id: int, actor: str, reason: str,
                           correlation_id: Optional[str] = None) -> Dict:
    actor, reason = str(actor or '').strip(), str(reason or '').strip()
    if not actor or len(reason) < 5:
        raise ValueError('actor e reason (mín. 5) são obrigatórios')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT * FROM monitoramento.agent_config_versions WHERE id=%s FOR UPDATE",
            (config_id,),
        )
        target = cursor.fetchone()
        if not target:
            raise LookupError('Configuração não encontrada')
        if target['status'] not in {'draft', 'active'}:
            raise ValueError('Somente configuração draft ou active pode ser ativada')
        cursor.execute(
            "SELECT id,autonomy_level FROM monitoramento.agent_autonomy_policies "
            "WHERE config_version_id=%s",
            (config_id,),
        )
        validate_activation_readiness(target,cursor.fetchone())
        active_key = str(target['agent_id'])
        cursor.execute(
            "SELECT * FROM monitoramento.agent_config_versions "
            "WHERE active_key=%s AND id<>%s FOR UPDATE",
            (active_key, config_id),
        )
        previous = cursor.fetchone()
        if previous:
            cursor.execute(
                "UPDATE monitoramento.agent_config_versions SET status='superseded',"
                "active_key=NULL,superseded_at=CURRENT_TIMESTAMP(6) WHERE id=%s",
                (previous['id'],),
            )
            cursor.execute(
                "INSERT INTO monitoramento.agent_config_audit "
                "(config_version_id,event_type,actor,reason,snapshot_json,correlation_id) "
                "VALUES(%s,'superseded',%s,%s,%s,%s)",
                (previous['id'], actor, reason, _canonical(_serialize(previous)), correlation_id),
            )
        cursor.execute(
            "UPDATE monitoramento.agent_config_versions SET status='active',active_key=%s,"
            "activated_at=COALESCE(activated_at,CURRENT_TIMESTAMP(6)) WHERE id=%s",
            (active_key, config_id),
        )
        cursor.execute(
            "SELECT v.*,a.agent_key,a.display_name,a.monitor_id "
            "FROM monitoramento.agent_config_versions v JOIN monitoramento.agent_definitions a "
            "ON a.id=v.agent_id WHERE v.id=%s",
            (config_id,),
        )
        row = cursor.fetchone()
        cursor.execute(
            "INSERT INTO monitoramento.agent_config_audit "
            "(config_version_id,event_type,actor,reason,snapshot_json,correlation_id) "
            "VALUES(%s,'activated',%s,%s,%s,%s)",
            (config_id, actor, reason, _canonical(_serialize(row)), correlation_id),
        )
        conn.commit()
        return _serialize(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
