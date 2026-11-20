"""Transcrição autorizada por referência segura e classificação estruturada."""

from dataclasses import dataclass
import hashlib
import json

from .action_queue_db import transition_action
from .monitor_db import get_connection

CLASSIFICATIONS={'owner_confirmed','owner_denied','no_answer','unclear','emergency','opt_out'}


@dataclass(frozen=True)
class VoiceAnalysis:
    transcript: str
    transcript_ref: str
    model_code: str
    model_version: str
    classification: str
    confidence: float
    reasons: tuple[str,...]


def secure_ref(value, field):
    ref=str(value or '').strip()
    if not ref.startswith(('vault:','TEST-','SANDBOX-')) or len(ref)>300:
        raise ValueError(f'{field} deve ser referência segura')
    return ref


def validate_analysis(value):
    if not isinstance(value,VoiceAnalysis):raise ValueError('Resultado de análise inválido')
    if not value.transcript.strip() or len(value.transcript)>20000:raise ValueError('Transcrição vazia ou acima do limite')
    secure_ref(value.transcript_ref,'transcript_ref')
    if value.classification not in CLASSIFICATIONS:raise ValueError('Classificação inválida')
    if not isinstance(value.confidence,(int,float)) or isinstance(value.confidence,bool) or not 0<=value.confidence<=1:raise ValueError('Confiança inválida')
    if not value.model_code or not value.model_version or len(value.reasons)>20:raise ValueError('Modelo ou evidências inválidos')
    review_required=value.confidence<0.8 or value.classification in {'unclear','emergency'}
    return {'review_status':'pending' if review_required else 'not_required','transcript_sha256':hashlib.sha256(value.transcript.encode()).hexdigest()}


class RuleBasedVoiceAnalyzer:
    """Baseline determinístico do sandbox; adaptadores externos usam o mesmo contrato."""
    model_code='voice-rules-sandbox';model_version='1.0'
    def analyze(self,transcript,transcript_ref):
        text=str(transcript or '').lower();classification='unclear';confidence=0.55;reasons=[]
        patterns=[('opt_out',('não me ligue','pare de ligar'),0.98),('emergency',('socorro','sequestro','emergência'),0.95),('owner_denied',('não reconheço','não autorizei'),0.9),('owner_confirmed',('está tudo bem','eu estou dirigindo','confirmo'),0.88)]
        for label,terms,score in patterns:
            found=[term for term in terms if term in text]
            if found:classification=label;confidence=score;reasons=[f'matched:{term}' for term in found];break
        return VoiceAnalysis(str(transcript),transcript_ref,self.model_code,self.model_version,classification,confidence,tuple(reasons))


def process_authorized_audio(payload, processor):
    """Orquestra o adaptador de transcrição sem entregar áudio não autorizado."""
    if payload.get('audio_authorized') is not True or not str(payload.get('authorization_source') or '').strip():
        raise PermissionError('Áudio sem autorização explícita')
    audio_ref = secure_ref(payload.get('audio_ref'), 'audio_ref')
    analysis = processor.transcribe_and_classify(audio_ref)
    validate_analysis(analysis)
    return record_voice_response(payload, analysis)


def record_voice_response(payload,analysis):
    event_id=str(payload.get('provider_event_id') or '').strip();call_id=str(payload.get('provider_call_id') or '').strip()
    audio_ref=secure_ref(payload.get('audio_ref'),'audio_ref');audio_hash=str(payload.get('audio_sha256') or '').lower()
    source=str(payload.get('authorization_source') or '').strip()
    if not event_id or not call_id or payload.get('audio_authorized') is not True or not source:raise ValueError('Evento, chamada e autorização explícita obrigatórios')
    if len(audio_hash)!=64 or any(c not in '0123456789abcdef' for c in audio_hash):raise ValueError('audio_sha256 inválido')
    validation=validate_analysis(analysis);structured={'classification':analysis.classification,'confidence':analysis.confidence,'reasons':list(analysis.reasons)}
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.voice_response_analyses WHERE provider_event_id=%s FOR UPDATE",(event_id,));existing=cursor.fetchone()
        if existing:conn.commit();existing['idempotent_replay']=True;return existing
        cursor.execute("""SELECT r.id receipt_id,r.action_id,a.public_id,a.status,a.version,a.idempotency_key
          FROM monitoramento.voice_dispatch_receipts r JOIN monitoramento.action_queue a ON a.id=r.action_id
          WHERE r.provider_call_id=%s FOR UPDATE""",(call_id,));linked=cursor.fetchone()
        if not linked:raise LookupError('Recibo de voz não encontrado')
        cursor.execute("""INSERT INTO monitoramento.voice_response_analyses
          (voice_receipt_id,action_id,provider_event_id,audio_ref,audio_sha256,audio_authorized,
           authorization_source,transcript_ref,transcript_sha256,model_code,model_version,
           classification,confidence,review_status,structured_result_json)
          VALUES(%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(
            linked['receipt_id'],linked['action_id'],event_id,audio_ref,audio_hash,source,
            analysis.transcript_ref,validation['transcript_sha256'],analysis.model_code,analysis.model_version,
            analysis.classification,analysis.confidence,validation['review_status'],json.dumps(structured,separators=(',',':'),sort_keys=True)))
        analysis_id=cursor.lastrowid
        if analysis.classification!='no_answer' and linked['status'] in {'sent','delivered'}:
            transition_action(linked['public_id'],'mark_responded',{'expected_version':linked['version'],'idempotency_key':f'{linked["idempotency_key"]}:voice-response:{event_id}','actor_type':'provider','actor_id':analysis.model_code},connection=conn)
        cursor.execute("SELECT * FROM monitoramento.voice_response_analyses WHERE id=%s",(analysis_id,));result=cursor.fetchone();conn.commit();result['idempotent_replay']=False;return result
    except Exception:
        if conn.in_transaction:conn.rollback()
        raise
    finally:cursor.close();conn.close()
