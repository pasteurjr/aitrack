from pathlib import Path

import pytest

from server.agent_autonomy import (
    AutonomyPolicy, authorize_decision, evaluate_autonomy, validate_policy,
)
MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '037_create_agent_autonomy_policies.sql'


def valid_decision():
    return {
        'schema_version': 'vehicle-monitoring-decision.v1',
        'classification': 'suspected_incident', 'confidence': .82,
        'summary': 'Saída de cerca com veículo armado requer confirmação.',
        'risk': {'level':'high','score':78,'rationale':'Movimento incompatível com a agenda.'},
        'evidence': [{'source':'tracker','type':'geofence_exit','ref':'incident:3516',
                      'summary':'Veículo cruzou a cerca permitida.'}],
        'proposed_actions': [{'type':'contact_owner','priority':'high',
                              'rationale':'Confirmar se a saída foi autorizada.',
                              'requires_approval':False}],
        'human_review': {'required':True,'reason':'Risco alto exige operador.',
                         'deadline_seconds':300},
    }


def policy(level='execute', risk='medium', actions=('contact_owner',)):
    return AutonomyPolicy(11, 7, level, risk, tuple(actions))


@pytest.mark.parametrize(
    ('level', 'disposition'),
    [('observe', 'observe_only'), ('recommend', 'recommended'), ('approval', 'approval_required')],
)
def test_non_executing_levels_never_mark_action_eligible(level, disposition):
    decision = valid_decision(); decision['risk'].update(level='low', score=20)
    decision['human_review'].update(required=False, reason='Revisão não exigida para risco baixo.')
    result = evaluate_autonomy(policy(level, 'none', ()), decision)
    assert result['actions'][0]['disposition'] == disposition


def test_execute_only_marks_explicit_low_risk_action_eligible():
    decision = valid_decision(); decision['risk'].update(level='low', score=20)
    decision['human_review'].update(required=False, reason='Revisão não exigida para risco baixo.')
    result = evaluate_autonomy(policy(), decision)
    assert result['actions'][0]['disposition'] == 'execution_eligible'
    assert result['human_review_required'] is False


@pytest.mark.parametrize('condition', ['risk', 'review', 'action', 'allowlist'])
def test_execute_fails_closed_to_approval(condition):
    decision = valid_decision(); decision['risk'].update(level='low', score=20)
    decision['human_review'].update(required=False, reason='Revisão não exigida para risco baixo.')
    current_policy = policy()
    if condition == 'risk': decision['risk'].update(level='high', score=80); decision['human_review']['required'] = True
    if condition == 'review': decision['human_review']['required'] = True
    if condition == 'action': decision['proposed_actions'][0].update(type='request_vehicle_command', requires_approval=True)
    if condition == 'allowlist': current_policy = policy(actions=('monitor',))
    result = evaluate_autonomy(current_policy, decision)
    assert result['actions'][0]['disposition'] == 'approval_required'
    assert result['actions'][0]['reasons'] and result['human_review_required'] is True


def test_policy_validation_forbids_misleading_or_sensitive_autonomy():
    assert validate_policy({'autonomy_level':'recommend','max_autonomous_risk':'none','allowed_autonomous_actions':[]})['autonomy_level']=='recommend'
    with pytest.raises(ValueError, match='Somente execute'):
        validate_policy({'autonomy_level':'recommend','max_autonomous_risk':'low','allowed_autonomous_actions':['monitor']})
    with pytest.raises(ValueError, match='sensível'):
        validate_policy({'autonomy_level':'execute','max_autonomous_risk':'low','allowed_autonomous_actions':['notify_authorities']})
    with pytest.raises(ValueError, match='inválido'):
        validate_policy({'autonomy_level':'execute','max_autonomous_risk':'low','allowed_autonomous_actions':[{}]})


def test_authorization_rejects_policy_from_another_version():
    with pytest.raises(ValueError, match='outra versão'):
        authorize_decision(8, valid_decision(), loader=lambda _id: policy())


def test_migration_persists_immutable_policy_and_authorization():
    sql = MIGRATION.read_text(encoding='utf-8').lower()
    for token in ('agent_autonomy_policies','autonomy_level','max_autonomous_risk',
                  'authorization_json','trg_agent_autonomy_draft_insert',
                  'trg_agent_autonomy_immutable_update','trg_agent_autonomy_immutable_delete'):
        assert token in sql
    assert 'drop table' not in sql and 'delete from' not in sql
