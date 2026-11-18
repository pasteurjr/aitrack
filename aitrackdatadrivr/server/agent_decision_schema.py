"""Validação estrita da decisão; texto livre nunca equivale a ação executada."""

import hashlib
import json
from datetime import datetime
from typing import Dict


SCHEMA_VERSION = 'vehicle-monitoring-decision.v1'
CLASSIFICATIONS = {
    'normal', 'attention', 'suspected_incident', 'confirmed_incident',
    'insufficient_evidence',
}
RISK_LEVELS = {'low', 'medium', 'high', 'critical'}
EVIDENCE_SOURCES = {'tracker', 'dirijabem', 'fused', 'system', 'operator'}
ACTION_TYPES = {
    'monitor', 'contact_owner', 'send_message', 'call_owner', 'notify_operator',
    'notify_authorities', 'request_vehicle_command',
}
PRIORITIES = {'low', 'normal', 'high', 'urgent'}
ROOT_FIELDS = {
    'schema_version', 'classification', 'confidence', 'summary', 'risk', 'evidence',
    'proposed_actions', 'human_review',
}
SENSITIVE_ACTIONS = {'notify_authorities', 'request_vehicle_command'}


class DecisionValidationError(ValueError):
    pass


def _object(value, fields, name):
    if not isinstance(value, dict):
        raise DecisionValidationError(f'{name} deve ser objeto')
    unknown = set(value) - fields
    if unknown:
        raise DecisionValidationError(f'{name} contém campos não permitidos: {sorted(unknown)}')
    return value


def _text(value, name, minimum=5, maximum=1000):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise DecisionValidationError(f'{name} deve ter entre {minimum} e {maximum} caracteres')
    return value.strip()


def _number(value, name, minimum, maximum):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise DecisionValidationError(f'{name} deve estar entre {minimum} e {maximum}')
    return value


def validate_decision(value: Dict) -> Dict:
    decision = _object(value, ROOT_FIELDS, 'decision')
    missing = ROOT_FIELDS - set(decision)
    if missing:
        raise DecisionValidationError(f'Campos obrigatórios ausentes: {sorted(missing)}')
    if decision['schema_version'] != SCHEMA_VERSION:
        raise DecisionValidationError(f'schema_version deve ser {SCHEMA_VERSION}')
    if decision['classification'] not in CLASSIFICATIONS:
        raise DecisionValidationError('classification inválida')
    _number(decision['confidence'], 'confidence', 0, 1)
    decision['summary'] = _text(decision['summary'], 'summary', 10, 1000)

    risk = _object(decision['risk'], {'level', 'score', 'rationale'}, 'risk')
    if set(risk) != {'level', 'score', 'rationale'} or risk['level'] not in RISK_LEVELS:
        raise DecisionValidationError('risk incompleto ou level inválido')
    _number(risk['score'], 'risk.score', 0, 100)
    risk['rationale'] = _text(risk['rationale'], 'risk.rationale')

    evidence = decision['evidence']
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 20:
        raise DecisionValidationError('evidence deve conter de 1 a 20 itens')
    evidence_fields = {'source', 'type', 'ref', 'summary', 'observed_at'}
    for index, item in enumerate(evidence):
        item = _object(item, evidence_fields, f'evidence[{index}]')
        if not {'source', 'type', 'ref', 'summary'} <= set(item):
            raise DecisionValidationError(f'evidence[{index}] incompleta')
        if item['source'] not in EVIDENCE_SOURCES:
            raise DecisionValidationError(f'evidence[{index}].source inválida')
        _text(item['type'], f'evidence[{index}].type', 1, 50)
        _text(item['ref'], f'evidence[{index}].ref', 1, 150)
        item['summary'] = _text(item['summary'], f'evidence[{index}].summary', 5, 500)
        if item.get('observed_at'):
            try:
                datetime.fromisoformat(item['observed_at'].replace('Z', '+00:00'))
            except (TypeError, ValueError):
                raise DecisionValidationError(f'evidence[{index}].observed_at inválido')

    actions = decision['proposed_actions']
    if not isinstance(actions, list) or len(actions) > 10:
        raise DecisionValidationError('proposed_actions deve ter no máximo 10 itens')
    action_fields = {'type', 'priority', 'rationale', 'requires_approval'}
    for index, action in enumerate(actions):
        action = _object(action, action_fields, f'proposed_actions[{index}]')
        if set(action) != action_fields:
            raise DecisionValidationError(f'proposed_actions[{index}] incompleta')
        if action['type'] not in ACTION_TYPES or action['priority'] not in PRIORITIES:
            raise DecisionValidationError(f'proposed_actions[{index}] inválida')
        if not isinstance(action['requires_approval'], bool):
            raise DecisionValidationError(f'proposed_actions[{index}].requires_approval inválido')
        action['rationale'] = _text(action['rationale'], f'proposed_actions[{index}].rationale', 5, 500)
        if action['type'] in SENSITIVE_ACTIONS and not action['requires_approval']:
            raise DecisionValidationError(f'{action["type"]} exige aprovação')

    review = _object(decision['human_review'], {'required', 'reason', 'deadline_seconds'}, 'human_review')
    if not {'required', 'reason'} <= set(review) or not isinstance(review['required'], bool):
        raise DecisionValidationError('human_review incompleta')
    review['reason'] = _text(review['reason'], 'human_review.reason', 5, 500)
    deadline = review.get('deadline_seconds')
    if deadline is not None and (
        not isinstance(deadline, int) or isinstance(deadline, bool) or not 0 <= deadline <= 86400
    ):
        raise DecisionValidationError('human_review.deadline_seconds inválido')
    if risk['level'] in {'high', 'critical'} and not review['required']:
        raise DecisionValidationError('Risco alto/crítico exige revisão humana')
    if decision['classification'] == 'insufficient_evidence' and not review['required']:
        raise DecisionValidationError('Evidência insuficiente exige revisão humana')
    return decision


def canonical_decision(value: Dict):
    validated = validate_decision(value)
    encoded = json.dumps(validated, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return encoded, hashlib.sha256(encoded.encode('utf-8')).hexdigest()
