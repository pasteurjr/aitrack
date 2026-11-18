"""Timeout sem confiança tardia, circuit breaker e fallback humano seguro."""

from dataclasses import replace
import json
import threading
import time
from typing import Callable, Optional

from .ai_provider import (
    DecisionProvider, DecisionRequest, DecisionResult, ProviderError,
    _validated_result,
)
from .agent_decision_schema import SCHEMA_VERSION


class CircuitOpenError(ProviderError):
    code = 'AI_CIRCUIT_OPEN'


class ProviderTimeoutError(ProviderError):
    code = 'AI_PROVIDER_TIMEOUT'


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_seconds=60,
                 clock: Callable[[], float] = time.monotonic):
        if failure_threshold < 1 or recovery_seconds < 1:
            raise ValueError('Limites do circuit breaker devem ser positivos')
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self.state = 'closed'
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None
        self._probe_in_flight = False
        self._lock = threading.Lock()

    def before_call(self):
        with self._lock:
            now = self.clock()
            if self.state == 'open':
                opened_at = self.opened_at if self.opened_at is not None else now
                if now - opened_at < self.recovery_seconds:
                    raise CircuitOpenError('Circuito do provedor está aberto')
                self.state = 'half_open'
                self._probe_in_flight = True
                return
            if self.state == 'half_open':
                if self._probe_in_flight:
                    raise CircuitOpenError('Circuito aguarda chamada de recuperação')
                self._probe_in_flight = True

    def record_success(self):
        with self._lock:
            self.state = 'closed'
            self.consecutive_failures = 0
            self.opened_at = None
            self._probe_in_flight = False

    def record_failure(self):
        with self._lock:
            self.consecutive_failures += 1
            self._probe_in_flight = False
            if self.state == 'half_open' or self.consecutive_failures >= self.failure_threshold:
                self.state = 'open'
                self.opened_at = self.clock()

    def snapshot(self):
        with self._lock:
            return {
                'state': self.state,
                'consecutive_failures': self.consecutive_failures,
                'failure_threshold': self.failure_threshold,
                'recovery_seconds': self.recovery_seconds,
                'opened_at_monotonic': self.opened_at,
            }


class SafeHumanFallbackProvider:
    provider_code = 'safe-human-fallback'

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        decision = {
            'schema_version': SCHEMA_VERSION,
            'classification': 'insufficient_evidence',
            'confidence': 0,
            'summary': 'A análise automática não foi concluída; revisão humana obrigatória.',
            'risk': {
                'level': 'medium', 'score': 50,
                'rationale': 'A indisponibilidade da IA impede reduzir o risco com segurança.',
            },
            'evidence': [{
                'source': 'system', 'type': 'ai_provider_unavailable',
                'ref': f'correlation:{request.correlation_id}',
                'summary': 'O provedor de IA não produziu decisão válida dentro dos limites.',
            }],
            'proposed_actions': [{
                'type': 'notify_operator', 'priority': 'high',
                'rationale': 'Encaminhar o caso para avaliação humana sem executar ação externa.',
                'requires_approval': False,
            }],
            'human_review': {
                'required': True,
                'reason': 'Fallback não substitui julgamento humano.',
                'deadline_seconds': 300,
            },
        }
        return _validated_result(
            self.provider_code, replace(request, model='rules-v1'),
            json.dumps(decision, ensure_ascii=False), 'safe-fallback', 0, 0,
        )


class ResilientDecisionProvider:
    def __init__(self, primary: DecisionProvider, breaker: CircuitBreaker,
                 fallback: Optional[DecisionProvider] = None,
                 clock: Callable[[], float] = time.monotonic):
        self.primary = primary
        self.provider_code = f'resilient:{primary.provider_code}'
        self.breaker = breaker
        self.fallback = fallback
        self.clock = clock
        self._metrics = {
            'calls': 0, 'primary_successes': 0, 'primary_failures': 0,
            'timeouts': 0, 'circuit_rejections': 0, 'fallbacks': 0,
        }
        self._lock = threading.Lock()

    def _increment(self, name):
        with self._lock:
            self._metrics[name] += 1

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        self._increment('calls')
        try:
            self.breaker.before_call()
        except CircuitOpenError as exc:
            self._increment('circuit_rejections')
            return self._fallback_or_raise(request, exc)

        started = self.clock()
        try:
            result = self.primary.generate_decision(request)
            elapsed = self.clock() - started
            if elapsed > request.timeout_seconds:
                raise ProviderTimeoutError(
                    f'Resposta tardia descartada após {elapsed:.3f}s',
                )
            self.breaker.record_success()
            self._increment('primary_successes')
            return result
        except Exception as exc:
            self.breaker.record_failure()
            self._increment('primary_failures')
            if isinstance(exc, (TimeoutError, ProviderTimeoutError)):
                self._increment('timeouts')
                if not isinstance(exc, ProviderTimeoutError):
                    exc = ProviderTimeoutError('Timeout do provedor')
            elif not isinstance(exc, ProviderError):
                exc = ProviderError('Falha não normalizada do provedor')
            return self._fallback_or_raise(request, exc)

    def _fallback_or_raise(self, request, error):
        if self.fallback is None:
            raise error
        self._increment('fallbacks')
        result = self.fallback.generate_decision(request)
        return replace(
            result, fallback_used=True, fallback_reason=getattr(error, 'code', type(error).__name__),
            primary_provider=self.primary.provider_code,
        )

    def snapshot(self):
        with self._lock:
            metrics = dict(self._metrics)
        return {'provider': self.primary.provider_code, 'metrics': metrics,
                'circuit': self.breaker.snapshot()}
