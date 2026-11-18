from dataclasses import replace

import pytest

from server.ai_provider import (
    DecisionRequest, DeterministicDecisionProvider, ProviderError,
)
from server.ai_resilience import (
    CircuitBreaker, CircuitOpenError, ProviderTimeoutError,
    ResilientDecisionProvider, SafeHumanFallbackProvider,
)
from server.agent_decision_schema import SCHEMA_VERSION


class Clock:
    def __init__(self): self.value = 0.0
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


class FailingProvider:
    provider_code = 'failing'
    def __init__(self, error=ProviderError('falha')): self.error = error; self.calls = 0
    def generate_decision(self, _request): self.calls += 1; raise self.error


class SlowProvider:
    provider_code = 'slow'
    def __init__(self, clock, delegate): self.clock=clock; self.delegate=delegate
    def generate_decision(self, request): self.clock.advance(request.timeout_seconds + 1); return self.delegate.generate_decision(request)


def safe_decision():
    return {
        'schema_version': SCHEMA_VERSION, 'classification': 'normal', 'confidence': 0.9,
        'summary': 'Nenhuma anomalia relevante foi identificada nas evidências.',
        'risk': {'level': 'low', 'score': 10, 'rationale': 'Telemetria dentro dos limites.'},
        'evidence': [{'source': 'tracker', 'type': 'position', 'ref': 'reading:1', 'summary': 'Posição atual válida.'}],
        'proposed_actions': [],
        'human_review': {'required': False, 'reason': 'Risco baixo com evidência suficiente.'},
    }


def request(timeout=10):
    return DecisionRequest(
        model='configured', instructions='Monitor responsável', input={}, context={},
        max_output_tokens=500, temperature=0, timeout_seconds=timeout,
        correlation_id='incident-1',
    )


def test_success_keeps_circuit_closed_and_does_not_use_fallback():
    clock=Clock(); primary=DeterministicDecisionProvider(safe_decision())
    resilient=ResilientDecisionProvider(primary,CircuitBreaker(clock=clock),SafeHumanFallbackProvider(),clock)
    result=resilient.generate_decision(request())
    assert result.fallback_used is False
    assert result.decision['classification']=='normal'
    snapshot=resilient.snapshot()
    assert snapshot['circuit']['state']=='closed'
    assert snapshot['metrics']['primary_successes']==1 and snapshot['metrics']['fallbacks']==0


def test_failures_open_circuit_and_later_calls_skip_primary():
    clock=Clock(); primary=FailingProvider(); breaker=CircuitBreaker(2,60,clock)
    resilient=ResilientDecisionProvider(primary,breaker,SafeHumanFallbackProvider(),clock)
    first=resilient.generate_decision(request()); second=resilient.generate_decision(request())
    third=resilient.generate_decision(request())
    assert all(item.fallback_used for item in (first,second,third))
    assert third.fallback_reason=='AI_CIRCUIT_OPEN'
    assert primary.calls==2 and resilient.snapshot()['circuit']['state']=='open'


def test_half_open_probe_recovers_circuit():
    clock=Clock(); failing=FailingProvider(); breaker=CircuitBreaker(1,30,clock)
    resilient=ResilientDecisionProvider(failing,breaker,SafeHumanFallbackProvider(),clock)
    resilient.generate_decision(request()); clock.advance(31)
    resilient.primary=DeterministicDecisionProvider(safe_decision())
    result=resilient.generate_decision(request())
    assert result.fallback_used is False
    assert resilient.snapshot()['circuit']['state']=='closed'


def test_late_result_is_discarded_and_safe_fallback_requires_human():
    clock=Clock(); delegate=DeterministicDecisionProvider(safe_decision())
    resilient=ResilientDecisionProvider(
        SlowProvider(clock,delegate),CircuitBreaker(1,30,clock),SafeHumanFallbackProvider(),clock,
    )
    result=resilient.generate_decision(request(5))
    assert result.fallback_used is True and result.fallback_reason=='AI_PROVIDER_TIMEOUT'
    assert result.decision['classification']=='insufficient_evidence'
    assert result.decision['human_review']['required'] is True
    assert result.decision['proposed_actions'][0]['type']=='notify_operator'
    assert resilient.snapshot()['metrics']['timeouts']==1


def test_native_timeout_is_normalized():
    clock=Clock(); resilient=ResilientDecisionProvider(
        FailingProvider(TimeoutError()),CircuitBreaker(2,30,clock),SafeHumanFallbackProvider(),clock,
    )
    result=resilient.generate_decision(request())
    assert result.fallback_reason=='AI_PROVIDER_TIMEOUT'


def test_without_fallback_error_remains_explicit():
    clock=Clock(); resilient=ResilientDecisionProvider(
        FailingProvider(),CircuitBreaker(1,30,clock),None,clock,
    )
    with pytest.raises(ProviderError): resilient.generate_decision(request())
    with pytest.raises(CircuitOpenError): resilient.generate_decision(request())


def test_fallback_never_claims_normality_or_external_execution():
    result=SafeHumanFallbackProvider().generate_decision(request())
    assert result.decision['confidence']==0
    assert result.decision['classification']=='insufficient_evidence'
    assert all(action['type']!='request_vehicle_command' for action in result.decision['proposed_actions'])
