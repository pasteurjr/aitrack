import copy
from pathlib import Path
import json

import pytest

from server.agent_decision_schema import (
    DecisionValidationError,
    SCHEMA_VERSION,
    canonical_decision,
    validate_decision,
)


SCHEMA_FILE = (
    Path(__file__).resolve().parents[1]
    / 'schemas'
    / 'vehicle_monitoring_decision_v1.json'
)
MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '034_structure_agent_decisions.sql'


def valid_decision():
    return {
        'schema_version': SCHEMA_VERSION,
        'classification': 'suspected_incident',
        'confidence': 0.82,
        'summary': 'Saída de cerca com veículo armado requer confirmação.',
        'risk': {'level': 'high', 'score': 78, 'rationale': 'Movimento incompatível com a agenda.'},
        'evidence': [{
            'source': 'tracker', 'type': 'geofence_exit', 'ref': 'incident:3516',
            'summary': 'Veículo cruzou a cerca permitida.',
            'observed_at': '2026-11-18T03:00:00-03:00',
        }],
        'proposed_actions': [{
            'type': 'contact_owner', 'priority': 'high',
            'rationale': 'Confirmar se a saída foi autorizada.', 'requires_approval': False,
        }],
        'human_review': {
            'required': True, 'reason': 'Risco alto exige operador.', 'deadline_seconds': 300,
        },
    }


def test_json_schema_artifact_is_strict_and_matches_runtime_version():
    schema = json.loads(SCHEMA_FILE.read_text(encoding='utf-8'))
    assert schema['$id'] == SCHEMA_VERSION
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(valid_decision())
    assert 'request_vehicle_command' in schema['properties']['proposed_actions']['items']['properties']['type']['enum']


def test_valid_decision_is_canonical_and_hash_repeatable():
    first, first_hash = canonical_decision(valid_decision())
    reordered = dict(reversed(list(valid_decision().items())))
    second, second_hash = canonical_decision(reordered)
    assert first == second
    assert first_hash == second_hash and len(first_hash) == 64


@pytest.mark.parametrize(
    ('mutate', 'match'),
    [
        (lambda d: d.update(extra='executed'), 'não permitidos'),
        (lambda d: d.update(confidence=1.1), 'confidence'),
        (lambda d: d.update(evidence=[]), 'evidence'),
        (lambda d: d['risk'].update(score=-1), 'risk.score'),
        (lambda d: d['human_review'].update(required=False), 'revisão humana'),
        (lambda d: (d.update(classification='insufficient_evidence'),
                    d['risk'].update(level='low', score=10),
                    d['human_review'].update(required=False)), 'Evidência insuficiente'),
        (lambda d: d['evidence'][0].update(observed_at='ontem'), 'observed_at'),
    ],
)
def test_rejects_malformed_unsafe_or_unreviewed_high_risk_decision(mutate, match):
    decision = copy.deepcopy(valid_decision())
    mutate(decision)
    with pytest.raises(DecisionValidationError, match=match):
        validate_decision(decision)


@pytest.mark.parametrize('action_type', ['notify_authorities', 'request_vehicle_command'])
def test_sensitive_actions_are_only_proposals_requiring_approval(action_type):
    decision = valid_decision()
    decision['proposed_actions'][0].update(type=action_type, requires_approval=False)
    with pytest.raises(DecisionValidationError, match='exige aprovação'):
        validate_decision(decision)


def test_migration_adds_validation_hash_without_rewriting_history():
    sql = MIGRATION.read_text(encoding='utf-8').lower()
    assert 'decision_sha256 char(64)' in sql
    assert 'validated_at datetime(6)' in sql
    assert 'delete from' not in sql and 'drop table' not in sql
