from types import SimpleNamespace
import json

import pytest

from server.ai_provider import (
    AnthropicDecisionProvider,
    DecisionRequest,
    DeterministicDecisionProvider,
    OpenAIDecisionProvider,
    ProviderConfigurationError,
    ProviderResponseError,
    create_provider,
)
from server.agent_decision_schema import SCHEMA_VERSION


def decision():
    return {
        'schema_version': SCHEMA_VERSION,
        'classification': 'attention',
        'confidence': 0.7,
        'summary': 'Veículo requer acompanhamento por evidência recente.',
        'risk': {'level': 'medium', 'score': 45, 'rationale': 'Há uma anomalia ainda não confirmada.'},
        'evidence': [{
            'source': 'tracker', 'type': 'offline', 'ref': 'episode:1',
            'summary': 'Telemetria interrompida acima do esperado.',
        }],
        'proposed_actions': [{
            'type': 'monitor', 'priority': 'normal',
            'rationale': 'Aguardar nova leitura antes de escalar.', 'requires_approval': False,
        }],
        'human_review': {'required': False, 'reason': 'Risco médio em observação.'},
    }


def request(model='configured-model'):
    return DecisionRequest(
        model=model, instructions='Atue como monitor veicular responsável.',
        input={'incident_id': 1}, context={'events': [1]}, max_output_tokens=1000,
        temperature=0.1, timeout_seconds=20, correlation_id='incident-1',
    )


def test_deterministic_provider_validates_same_contract_without_external_call():
    result = DeterministicDecisionProvider(decision()).generate_decision(request())
    assert result.provider == 'deterministic-test'
    assert result.model == 'configured-model'
    assert result.input_tokens == 0 and result.output_tokens == 0
    assert len(result.decision_sha256) == 64


def test_anthropic_adapter_uses_configured_model_and_normalizes_usage():
    calls = []
    response = SimpleNamespace(
        id='msg-1', content=[SimpleNamespace(type='text', text=json.dumps(decision()))],
        usage=SimpleNamespace(input_tokens=123, output_tokens=45),
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or response))
    result = AnthropicDecisionProvider('secret', client).generate_decision(request('claude-configured'))
    assert calls[0]['model'] == 'claude-configured'
    assert calls[0]['timeout'] == 20
    assert 'proposed_actions' in calls[0]['messages'][0]['content']
    assert result.provider_request_id == 'msg-1'
    assert (result.input_tokens, result.output_tokens) == (123, 45)


def test_openai_adapter_uses_responses_api_configured_model_and_no_storage():
    calls = []
    response = SimpleNamespace(
        id='resp-1', output_text=json.dumps(decision()),
        usage=SimpleNamespace(input_tokens=50, output_tokens=20),
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or response))
    result = OpenAIDecisionProvider('secret', client).generate_decision(request('gpt-configured'))
    assert calls[0]['model'] == 'gpt-configured'
    assert calls[0]['store'] is False
    assert calls[0]['timeout'] == 20
    assert result.provider == 'openai' and result.provider_request_id == 'resp-1'


@pytest.mark.parametrize('adapter', ['anthropic', 'openai'])
def test_factory_requires_secret_and_never_falls_back(adapter):
    with pytest.raises(ProviderConfigurationError):
        create_provider(adapter, {})


def test_factory_rejects_unknown_provider():
    with pytest.raises(ProviderConfigurationError, match='não suportado'):
        create_provider('deepseek', {'DEEPSEEK_API_KEY': 'secret'})


@pytest.mark.parametrize('provider_class', [AnthropicDecisionProvider, OpenAIDecisionProvider])
def test_adapter_rejects_non_json_or_contract_violation(provider_class):
    if provider_class is AnthropicDecisionProvider:
        response = SimpleNamespace(
            id='bad', content=[SimpleNamespace(type='text', text='não é json')],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_kwargs: response))
    else:
        response = SimpleNamespace(
            id='bad', output_text='{}', usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )
        client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_kwargs: response))
    with pytest.raises(ProviderResponseError):
        provider_class('secret', client).generate_decision(request())


def test_prompt_does_not_claim_actions_were_executed():
    calls = []
    response = SimpleNamespace(
        id='msg', content=[SimpleNamespace(type='text', text=json.dumps(decision()))],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or response))
    AnthropicDecisionProvider('secret', client).generate_decision(request())
    prompt = calls[0]['messages'][0]['content']
    assert 'Não afirme que uma ação foi executada' in prompt
    assert 'incident_id' in prompt
