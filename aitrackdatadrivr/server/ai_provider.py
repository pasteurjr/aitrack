"""Interface de provedor de IA sem acoplamento do domínio a SDK externo."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Dict, Mapping, Optional, Protocol

from .agent_decision_schema import canonical_decision


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / 'schemas'
    / 'vehicle_monitoring_decision_v1.json'
)


class ProviderError(RuntimeError):
    code = 'AI_PROVIDER_ERROR'


class ProviderConfigurationError(ProviderError):
    code = 'AI_PROVIDER_CONFIGURATION_ERROR'


class ProviderResponseError(ProviderError):
    code = 'AI_PROVIDER_INVALID_RESPONSE'


@dataclass(frozen=True)
class DecisionRequest:
    model: str
    instructions: str
    input: Dict
    context: Dict
    max_output_tokens: int
    temperature: float
    timeout_seconds: int
    correlation_id: str


@dataclass(frozen=True)
class DecisionResult:
    provider: str
    model: str
    provider_request_id: Optional[str]
    decision: Dict
    canonical_json: str
    decision_sha256: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[float] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    primary_provider: Optional[str] = None


class DecisionProvider(Protocol):
    provider_code: str

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        ...


def _schema_prompt(request: DecisionRequest) -> str:
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    payload = json.dumps(
        {'input': request.input, 'context': request.context},
        ensure_ascii=False, separators=(',', ':'), sort_keys=True,
    )
    return (
        "Responda exclusivamente com um objeto JSON válido, sem markdown. "
        "Não afirme que uma ação foi executada; preencha apenas proposed_actions.\n"
        f"JSON Schema obrigatório:\n{schema}\n"
        f"Dados da análise:\n{payload}"
    )


def _validated_result(provider: str, request: DecisionRequest, raw_text: str,
                      request_id=None, input_tokens=None, output_tokens=None):
    try:
        value = json.loads(raw_text)
        canonical, digest = canonical_decision(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderResponseError(f'Resposta de {provider} não atende ao contrato v1') from exc
    return DecisionResult(
        provider=provider, model=request.model, provider_request_id=request_id,
        decision=value, canonical_json=canonical, decision_sha256=digest,
        input_tokens=input_tokens, output_tokens=output_tokens,
    )


class AnthropicDecisionProvider:
    provider_code = 'anthropic'

    def __init__(self, api_key: str, client=None):
        if not api_key:
            raise ProviderConfigurationError('ANTHROPIC_API_KEY não configurada')
        if client is None:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
        self.client = client

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        try:
            response = self.client.messages.create(
                model=request.model,
                max_tokens=request.max_output_tokens,
                temperature=request.temperature,
                timeout=request.timeout_seconds,
                system=request.instructions,
                messages=[{'role': 'user', 'content': _schema_prompt(request)}],
            )
            text = ''.join(
                block.text for block in response.content
                if getattr(block, 'type', None) == 'text'
            )
            usage = getattr(response, 'usage', None)
            return _validated_result(
                self.provider_code, request, text, getattr(response, 'id', None),
                getattr(usage, 'input_tokens', None), getattr(usage, 'output_tokens', None),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f'Falha no provedor {self.provider_code}') from exc


class OpenAIDecisionProvider:
    provider_code = 'openai'

    def __init__(self, api_key: str, client=None):
        if not api_key:
            raise ProviderConfigurationError('OPENAI_API_KEY não configurada')
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
        self.client = client

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        try:
            response = self.client.responses.create(
                model=request.model,
                instructions=request.instructions,
                input=_schema_prompt(request),
                max_output_tokens=request.max_output_tokens,
                temperature=request.temperature,
                timeout=request.timeout_seconds,
                store=False,
            )
            usage = getattr(response, 'usage', None)
            return _validated_result(
                self.provider_code, request, response.output_text,
                getattr(response, 'id', None), getattr(usage, 'input_tokens', None),
                getattr(usage, 'output_tokens', None),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f'Falha no provedor {self.provider_code}') from exc


class DeterministicDecisionProvider:
    """Somente testes; factory exige opt-in explícito para impedir uso silencioso."""
    provider_code = 'deterministic-test'

    def __init__(self, decision: Dict):
        self.decision = decision

    def generate_decision(self, request: DecisionRequest) -> DecisionResult:
        return _validated_result(
            self.provider_code, request,
            json.dumps(self.decision, ensure_ascii=False), 'deterministic-test', 0, 0,
        )


def create_provider(provider_code: str, environ: Mapping[str, str] = os.environ,
                    client=None) -> DecisionProvider:
    code = str(provider_code or '').strip().lower()
    if code == 'anthropic':
        return AnthropicDecisionProvider(environ.get('ANTHROPIC_API_KEY', ''), client)
    if code == 'openai':
        return OpenAIDecisionProvider(environ.get('OPENAI_API_KEY', ''), client)
    raise ProviderConfigurationError(f'Provedor não suportado: {code or "ausente"}')
