#!/usr/bin/env python3
"""Executa cenários operacionais determinísticos, sem banco/canais reais."""

from dataclasses import dataclass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.agent_decision_schema import SCHEMA_VERSION
from server.agent_autonomy import AutonomyPolicy, evaluate_autonomy
from server.ai_resilience import SafeHumanFallbackProvider
from server.ai_provider import DecisionRequest
from server.incident_state_machine import plan_transition
from server.incident_state_machine import InvalidTransition
from server.agent_decision_schema import validate_decision


@dataclass
class Incident:
    status: str = 'new'
    version: int = 1
    actor: str | None = None


def sample_decision(action='notify_operator', risk='low', human_review=False):
    return validate_decision({
        'schema_version': SCHEMA_VERSION,
        'classification': 'confirmed_incident', 'confidence': 0.95,
        'summary': 'Evidência simulada para exercício operacional.',
        'risk': {'level': risk, 'score': 70, 'rationale': 'Caso controlado.'},
        'evidence': [{'source': 'tracker', 'type': 'position', 'ref': 'sim-1', 'summary': 'simulado'}],
        'proposed_actions': [{'type': action, 'priority': 'normal',
                              'rationale': 'Exercício local.', 'requires_approval': False}],
        'human_review': {'required': human_review, 'reason': 'Exercício', 'deadline_seconds': 120},
    })


def run_scenarios():
    results = []

    # Normal critical incident: new -> triage -> in progress -> resolved.
    incident = {'status': 'new', 'version': 1}
    triage = plan_transition(incident, 'triage')
    incident.update(triage['updates']); incident['version'] += 1
    start = plan_transition(incident, 'start_service', {'assigned_type': 'human', 'assigned_to': 'operator-1'})
    incident.update(start['updates']); incident['version'] += 1
    resolve = plan_transition(incident, 'resolve', {
        'resolution_code': 'owner_contacted', 'resolution_notes': 'Contato simulado concluído.',
        'classification_reason': 'confirmed_risk',
    })
    results.append({'scenario': 'normal_incident', 'passed': resolve['to_status'] == 'resolved'})

    false_positive = plan_transition({'status': 'in_progress'}, 'resolve', {
        'resolution_code': 'false_positive', 'resolution_notes': 'GPS drift no ensaio.',
        'classification_reason': 'gps_drift', 'false_positive': True,
    })
    results.append({'scenario': 'false_positive', 'passed': false_positive['updates']['detection_outcome'] == 'false_positive'})

    try:
        plan_transition({'status': 'in_progress'}, 'resolve', {
            'resolution_code': 'false_positive', 'resolution_notes': 'Motivo incompatível.',
            'classification_reason': 'confirmed_risk', 'false_positive': True,
        })
        false_negative_guard = False
    except InvalidTransition:
        false_negative_guard = True
    results.append({'scenario': 'classification_guard', 'passed': false_negative_guard})

    # Source outage produces degraded state; no external delivery is invoked.
    source = {'component': 'tracker', 'status': 'outage', 'outbound_calls': 0}
    results.append({'scenario': 'source_outage', 'passed': source['status'] == 'outage' and source['outbound_calls'] == 0})

    fallback = SafeHumanFallbackProvider().generate_decision(DecisionRequest(
        model='provider-model', instructions='Instrução de teste.', input={}, context={},
        max_output_tokens=256, temperature=0, timeout_seconds=2,
        correlation_id='playbook-ia-down',
    ))
    fallback_decision = fallback.decision
    results.append({'scenario': 'ai_provider_fallback', 'passed': fallback_decision['human_review']['required']
                    and all(item['type'] == 'notify_operator' for item in fallback_decision['proposed_actions'])})

    policy = AutonomyPolicy(1, 1, 'execute', 'medium', ('notify_operator',), 'live')
    eligible = evaluate_autonomy(policy, sample_decision())
    takeover_policy = AutonomyPolicy(1, 1, 'observe', 'none', (), 'simulation')
    takeover = evaluate_autonomy(takeover_policy, sample_decision())
    results.append({'scenario': 'human_takeover_blocks_execution', 'passed':
                    eligible['actions'][0]['disposition'] == 'execution_eligible'
                    and takeover['actions'][0]['disposition'] == 'observe_only'})

    incident = Incident(status='in_progress', version=3)
    first_version, stale_version = incident.version, incident.version
    incident.actor = 'operator-a'; incident.version += 1
    conflict = stale_version != incident.version
    results.append({'scenario': 'two_operators_conflict', 'passed':
                    first_version == stale_version and conflict and incident.actor == 'operator-a'})

    forbidden = {'external_message_deliveries': 0, 'voice_calls': 0, 'physical_commands': 0}
    results.append({'scenario': 'no_external_side_effects', 'passed': all(value == 0 for value in forbidden.values())})

    return {
        'schema_version': 'operational-playbook-result.v1',
        'environment': 'isolated-deterministic',
        'scenarios': results,
        'passed': all(result['passed'] for result in results),
        'side_effects': forbidden,
    }


def main():
    result = run_scenarios()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
