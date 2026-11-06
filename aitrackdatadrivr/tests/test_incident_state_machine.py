from datetime import datetime, timedelta

import pytest

from server.incident_state_machine import InvalidTransition, plan_transition


NOW = datetime(2026, 11, 6, 14, 30)


def _incident(status, **overrides):
    return {'status': status, 'acknowledged_at': None, 'resolution_code': None, **overrides}


@pytest.mark.parametrize(
    ('status', 'command', 'expected_status'),
    [
        ('new', 'triage', 'triage'),
        ('waiting_response', 'resume', 'in_progress'),
        ('in_progress', 'escalate', 'escalated'),
        ('escalated', 'resume', 'in_progress'),
        ('resolved', 'reopen', 'triage'),
        ('closed', 'reopen', 'triage'),
    ],
)
def test_allows_simple_lifecycle_transitions(status, command, expected_status):
    plan = plan_transition(_incident(status), command, now=NOW)

    assert plan['from_status'] == status
    assert plan['to_status'] == expected_status
    assert plan['updates']['status'] == expected_status


def test_triage_records_timestamp():
    plan = plan_transition(_incident('new'), 'triage', now=NOW)

    assert plan['updates']['triaged_at'] == NOW


def test_start_service_requires_and_records_assignee():
    with pytest.raises(InvalidTransition, match='responsável'):
        plan_transition(_incident('triage'), 'start_service', now=NOW)

    plan = plan_transition(
        _incident('triage'),
        'start_service',
        {'assigned_type': 'agent', 'assigned_to': 'agente-seguranca'},
        NOW,
    )

    assert plan['to_status'] == 'in_progress'
    assert plan['updates']['assigned_type'] == 'agent'
    assert plan['updates']['acknowledged_at'] == NOW


def test_waiting_requires_next_action():
    with pytest.raises(InvalidTransition, match='next_action_at'):
        plan_transition(_incident('in_progress'), 'wait_response', now=NOW)

    next_action = NOW + timedelta(minutes=15)
    plan = plan_transition(
        _incident('in_progress'),
        'wait_response',
        {'next_action_at': next_action},
        NOW,
    )
    assert plan['updates']['next_action_at'] == next_action


def test_resolve_requires_classification_and_justification():
    with pytest.raises(InvalidTransition, match='código e justificativa'):
        plan_transition(_incident('in_progress'), 'resolve', now=NOW)

    plan = plan_transition(
        _incident('in_progress'),
        'resolve',
        {
            'resolution_code': 'owner_confirmed_safe',
            'resolution_notes': 'Dono confirmou segurança.',
            'classification_reason': 'owner_confirmed',
        },
        NOW,
    )
    assert plan['to_status'] == 'resolved'
    assert plan['updates']['resolved_at'] == NOW
    assert plan['updates']['next_action_at'] is None
    assert plan['updates']['detection_outcome'] == 'true_positive'


def test_false_positive_requires_matching_code():
    with pytest.raises(InvalidTransition, match='false_positive'):
        plan_transition(
            _incident('triage'),
            'resolve',
            {
                'resolution_code': 'safe', 'resolution_notes': 'Evento sem risco.',
                'false_positive': True, 'classification_reason': 'sensor_noise',
            },
            NOW,
        )

    plan = plan_transition(
        _incident('triage'),
        'resolve',
        {
            'resolution_code': 'false_positive',
            'resolution_notes': 'Ruído confirmado no sensor.',
            'false_positive': True,
            'classification_reason': 'sensor_noise',
        },
        NOW,
    )
    assert plan['updates']['detection_outcome'] == 'false_positive'
    assert plan['updates']['classification_reason'] == 'sensor_noise'


def test_resolution_rejects_reason_from_wrong_outcome_taxonomy():
    with pytest.raises(InvalidTransition, match='Motivo de classificação'):
        plan_transition(
            _incident('in_progress'),
            'resolve',
            {
                'resolution_code': 'confirmed',
                'resolution_notes': 'Ocorrência confirmada.',
                'classification_reason': 'gps_drift',
            },
            NOW,
        )


def test_close_requires_prior_resolution():
    with pytest.raises(InvalidTransition, match='resolução registrada'):
        plan_transition(_incident('resolved'), 'close', now=NOW)

    plan = plan_transition(
        _incident('resolved', resolution_code='owner_confirmed_safe'),
        'close',
        now=NOW,
    )
    assert plan['updates']['closed_at'] == NOW


def test_reopen_clears_resolution_data():
    plan = plan_transition(
        _incident('closed', resolution_code='safe', resolved_at=NOW, closed_at=NOW),
        'reopen',
        now=NOW,
    )

    assert plan['updates']['resolution_code'] is None
    assert plan['updates']['resolution_notes'] is None
    assert plan['updates']['resolved_at'] is None
    assert plan['updates']['closed_at'] is None
    assert plan['updates']['false_positive'] is False


@pytest.mark.parametrize(
    ('status', 'command'),
    [('new', 'close'), ('new', 'resolve'), ('closed', 'triage'), ('resolved', 'escalate')],
)
def test_rejects_illegal_transitions(status, command):
    with pytest.raises(InvalidTransition, match='não permitido'):
        plan_transition(_incident(status), command, now=NOW)


def test_rejects_values_that_exceed_database_contract():
    with pytest.raises(InvalidTransition, match='100 caracteres'):
        plan_transition(
            _incident('triage'),
            'start_service',
            {'assigned_type': 'human', 'assigned_to': 'x' * 101},
            NOW,
        )

    with pytest.raises(InvalidTransition, match='50 caracteres'):
        plan_transition(
            _incident('in_progress'),
            'resolve',
            {'resolution_code': 'x' * 51, 'resolution_notes': 'Justificativa válida.'},
            NOW,
        )
