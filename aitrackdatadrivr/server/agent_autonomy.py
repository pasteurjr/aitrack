"""Política fail-closed: decidir não equivale a executar uma ação."""

from dataclasses import dataclass
import json
from typing import Callable, Dict, Optional

from .agent_decision_schema import ACTION_TYPES, SENSITIVE_ACTIONS, validate_decision
from .monitor_db import get_connection


AUTONOMY_LEVELS = {'observe', 'recommend', 'approval', 'execute'}
AUTONOMOUS_RISKS = {'none', 'low', 'medium'}
RISK_RANK = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}


@dataclass(frozen=True)
class AutonomyPolicy:
    policy_id: int
    config_version_id: int
    autonomy_level: str
    max_autonomous_risk: str
    allowed_autonomous_actions: tuple[str, ...]
    execution_mode: str = 'simulation'


def validate_policy(value: Dict) -> Dict:
    if not isinstance(value, dict) or not set(value) <= {
        'autonomy_level', 'max_autonomous_risk', 'allowed_autonomous_actions',
        'execution_mode',
    } or not {'autonomy_level','max_autonomous_risk','allowed_autonomous_actions'} <= set(value):
        raise ValueError('Política de autonomia possui campos inválidos')
    level, risk, actions = (
        value['autonomy_level'], value['max_autonomous_risk'],
        value['allowed_autonomous_actions'],
    )
    execution_mode=value.get('execution_mode','simulation')
    if execution_mode not in {'simulation','live'}:
        raise ValueError('execution_mode inválido')
    if not isinstance(level, str) or not isinstance(risk, str) or (
        level not in AUTONOMY_LEVELS or risk not in AUTONOMOUS_RISKS
    ):
        raise ValueError('Nível de autonomia ou risco máximo inválido')
    if not isinstance(actions, list) or any(
        not isinstance(action, str) or action not in ACTION_TYPES for action in actions
    ):
        raise ValueError('allowed_autonomous_actions inválido')
    actions = sorted(set(actions))
    if level != 'execute' and (risk != 'none' or actions):
        raise ValueError('Somente execute pode declarar risco e ações autônomas')
    if level == 'execute' and (risk == 'none' or not actions):
        raise ValueError('execute exige risco baixo/médio e ao menos uma ação')
    if set(actions) & SENSITIVE_ACTIONS:
        raise ValueError('Ação sensível nunca pode ser autônoma')
    return {
        'autonomy_level': level,
        'max_autonomous_risk': risk,
        'allowed_autonomous_actions': actions,
        'execution_mode':execution_mode,
    }


def evaluate_autonomy(policy: AutonomyPolicy, decision: Dict,
                      safety_context: Optional[Dict] = None) -> Dict:
    decision = validate_decision(decision)
    level = policy.autonomy_level
    max_rank = RISK_RANK.get(policy.max_autonomous_risk, 0)
    decision_risk = decision['risk']['level']
    trusted_severity = str((safety_context or {}).get('severity') or '').strip().lower()
    trusted_review_required = trusted_severity in {'high', 'critical'}
    authorizations = []
    for index, action in enumerate(decision['proposed_actions']):
        reasons = []
        if level == 'observe':
            disposition = 'observe_only'
        elif level == 'recommend':
            disposition = 'recommended'
        elif level == 'approval':
            disposition = 'approval_required'
            reasons.append('policy_requires_approval')
        else:
            if decision['human_review']['required'] or trusted_review_required:
                reasons.append('decision_requires_human_review')
            if action['requires_approval']:
                reasons.append('action_requires_approval')
            if action['type'] in SENSITIVE_ACTIONS:
                reasons.append('sensitive_action')
            if RISK_RANK[decision_risk] > max_rank:
                reasons.append('risk_above_autonomous_limit')
            if action['type'] not in policy.allowed_autonomous_actions:
                reasons.append('action_not_in_autonomous_allowlist')
            disposition = 'approval_required' if reasons else (
                'simulated' if policy.execution_mode=='simulation' else 'execution_eligible'
            )
        authorizations.append({
            'action_index': index,
            'action_type': action['type'],
            'disposition': disposition,
            'reasons': reasons,
        })
    return {
        'schema_version': 'agent-autonomy-authorization.v1',
        'autonomy_policy_id': policy.policy_id,
        'config_version_id': policy.config_version_id,
        'autonomy_level': level,
        'execution_mode':policy.execution_mode,
        'decision_risk': decision_risk,
        'human_review_required': decision['human_review']['required'] or trusted_review_required or any(
            item['disposition'] == 'approval_required' for item in authorizations
        ),
        'trusted_incident_severity': trusted_severity or None,
        'actions': authorizations,
    }


def load_autonomy_policy(config_version_id: int) -> AutonomyPolicy:
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id,config_version_id,autonomy_level,execution_mode,max_autonomous_risk,"
            "allowed_autonomous_actions_json FROM monitoramento.agent_autonomy_policies "
            "WHERE config_version_id=%s",
            (config_version_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise LookupError('Configuração não possui política de autonomia')
        value = validate_policy({
            'autonomy_level': row['autonomy_level'],
            'max_autonomous_risk': row['max_autonomous_risk'],
            'allowed_autonomous_actions': json.loads(row['allowed_autonomous_actions_json']),
            'execution_mode':row['execution_mode'],
        })
        return AutonomyPolicy(
            row['id'], row['config_version_id'], value['autonomy_level'],
            value['max_autonomous_risk'], tuple(value['allowed_autonomous_actions']),value['execution_mode'],
        )
    finally:
        cursor.close(); conn.close()


def authorize_decision(config_version_id: int, decision: Dict,
                       loader: Optional[Callable] = None,
                       safety_context: Optional[Dict] = None) -> Dict:
    policy = (loader or load_autonomy_policy)(config_version_id)
    if policy.config_version_id != config_version_id:
        raise ValueError('Política de autonomia pertence a outra versão')
    return evaluate_autonomy(policy, decision, safety_context)


def add_autonomy_policy(config_version_id: int, value: Dict,
                        actor: str, reason: str) -> int:
    value = validate_policy(value)
    actor, reason = str(actor or '').strip(), str(reason or '').strip()
    if not actor or len(reason) < 5:
        raise ValueError('actor e reason são obrigatórios')
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT status FROM monitoramento.agent_config_versions WHERE id=%s FOR UPDATE",
            (config_version_id,),
        )
        config = cursor.fetchone()
        if not config:
            raise LookupError('Configuração não encontrada')
        if config['status'] != 'draft':
            raise ValueError('Política de autonomia exige configuração draft')
        cursor.execute(
            "INSERT INTO monitoramento.agent_autonomy_policies "
            "(config_version_id,autonomy_level,execution_mode,max_autonomous_risk,"
            "allowed_autonomous_actions_json,created_by,change_reason) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (config_version_id, value['autonomy_level'],value['execution_mode'], value['max_autonomous_risk'],
             json.dumps(value['allowed_autonomous_actions'], separators=(',', ':')),
             actor, reason),
        )
        policy_id = cursor.lastrowid; conn.commit(); return policy_id
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()
