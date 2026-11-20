from pathlib import Path
import pytest
from server import voice_response_db
from server.voice_response_db import RuleBasedVoiceAnalyzer,VoiceAnalysis,process_authorized_audio,secure_ref,validate_analysis

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'052_create_voice_response_analyses.sql'


def test_sandbox_analyzer_returns_structured_classification_without_persisting_text():
    analyzer=RuleBasedVoiceAnalyzer();result=analyzer.analyze('Confirmo, eu estou dirigindo e está tudo bem.','vault:transcripts/1')
    validation=validate_analysis(result)
    assert result.classification=='owner_confirmed' and result.confidence>=0.8
    assert validation['review_status']=='not_required' and len(validation['transcript_sha256'])==64


def test_emergency_unclear_and_low_confidence_require_human_review():
    analyzer=RuleBasedVoiceAnalyzer()
    assert validate_analysis(analyzer.analyze('Socorro, emergência!','TEST-TRANSCRIPT-1'))['review_status']=='pending'
    assert validate_analysis(analyzer.analyze('alô?','TEST-TRANSCRIPT-2'))['review_status']=='pending'
    low=VoiceAnalysis('sim','vault:t/3','model','1','owner_confirmed',0.5,())
    assert validate_analysis(low)['review_status']=='pending'


def test_audio_and_transcript_references_fail_closed():
    assert secure_ref('vault:audio/123','audio_ref')
    with pytest.raises(ValueError,match='referência segura'):secure_ref('/tmp/audio.wav','audio_ref')
    with pytest.raises(ValueError,match='referência segura'):secure_ref('https://public.example/audio','audio_ref')


def test_processor_never_receives_unauthorized_audio_and_authorized_result_is_persisted(monkeypatch):
    class Processor:
        calls=[]
        def transcribe_and_classify(self,audio_ref):
            self.calls.append(audio_ref)
            return VoiceAnalysis('Tudo bem','vault:transcripts/7','sandbox-stt','1','owner_confirmed',0.9,('test',))
    processor=Processor();payload={'audio_ref':'vault:audio/7','audio_authorized':False,'authorization_source':''}
    with pytest.raises(PermissionError,match='autorização'):
        process_authorized_audio(payload,processor)
    assert processor.calls==[]
    payload.update(audio_authorized=True,authorization_source='owner-consent')
    monkeypatch.setattr(voice_response_db,'record_voice_response',lambda body,analysis:{'stored':True,'classification':analysis.classification})
    assert process_authorized_audio(payload,processor)=={'stored':True,'classification':'owner_confirmed'}
    assert processor.calls==['vault:audio/7']


def test_migration_requires_authorization_model_confidence_review_and_no_raw_audio():
    sql=MIGRATION.read_text().lower()
    for token in ('voice_response_analyses','audio_authorized','authorization_source','transcript_ref','transcript_sha256','model_code','classification','confidence','review_status'):
        assert token in sql
    assert 'blob' not in sql and 'voice response analysis is immutable' in sql
