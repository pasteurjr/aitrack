from pathlib import Path
import pytest

from server.action_retry_db import failure_is_retryable
from server.message_sandbox import MessageSandboxError, SandboxMessageProvider
from server.voice_response_db import RuleBasedVoiceAnalyzer
from server.voice_sandbox import SandboxVoiceProvider, VoiceSandboxError


@pytest.mark.parametrize('code', ['INVALID_DESTINATION','INVALID_NUMBER','UNKNOWN_SUBSCRIBER','OPT_OUT','CONSENT_REVOKED','DESTINATION_BLOCKED'])
def test_permanent_refusal_or_invalid_destination_never_retries(code):
    assert not failure_is_retryable(code)


@pytest.mark.parametrize('code', ['PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE','NO_RESPONSE','NO_ANSWER'])
def test_transient_failure_or_silence_is_bounded_retry(code):
    assert failure_is_retryable(code)


def test_message_timeout_is_normalized_without_network_retry_inside_provider():
    provider=SandboxMessageProvider('https://sandbox.example/messages','x',{'TEST-OWNER'},
        opener=lambda *_args,**_kwargs: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(MessageSandboxError) as captured:
        provider.send('TEST-OWNER','teste','corr-1')
    assert captured.value.code=='PROVIDER_TIMEOUT'


def test_voice_timeout_is_normalized_and_opt_out_is_classified():
    provider=SandboxVoiceProvider('https://sandbox.example/calls','x',{'TEST-OWNER'},
        opener=lambda *_args,**_kwargs: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(VoiceSandboxError) as captured:
        provider.call('TEST-OWNER','Sou um assistente virtual automatizado.','action-1')
    assert captured.value.code=='PROVIDER_TIMEOUT'
    result=RuleBasedVoiceAnalyzer().analyze('Não me ligue novamente.','TEST-TRANSCRIPT')
    assert result.classification=='opt_out' and result.confidence>=0.95


def test_outcome_code_has_no_dependency_on_mock_data():
    roots=Path(__file__).resolve().parents[1]
    sources='\n'.join((roots/'server'/name).read_text() for name in (
        'action_retry_db.py','message_event_db.py','voice_response_db.py'))
    assert 'mockData' not in sources and 'random.' not in sources
    assert "MAX(occurred_at) sent_at" in sources
