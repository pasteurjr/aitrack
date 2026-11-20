"""Chamada de voz somente em sandbox, roteiro aprovado e aviso de automação."""

from dataclasses import dataclass
import hashlib
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .action_queue_db import transition_action
from .message_template_db import render_body
from .monitor_db import get_connection

DISCLOSURES = ('assistente virtual automatizado', 'ligação automatizada', 'chamada automatizada')


class VoiceSandboxError(RuntimeError):
    code = 'VOICE_SANDBOX_ERROR'


@dataclass(frozen=True)
class VoiceReceipt:
    provider_code: str
    provider_call_id: str
    destination_hash: str
    script_sha256: str
    request_sha256: str
    http_status: int
    response: dict


def validate_automation_disclosure(script):
    normalized = str(script or '').strip().lower()
    if not any(marker in normalized for marker in DISCLOSURES):
        raise VoiceSandboxError('Roteiro deve identificar claramente a automação')
    if len(normalized) > 10000:
        raise VoiceSandboxError('Roteiro acima de 10000 caracteres')
    return True


class SandboxVoiceProvider:
    provider_code = 'http-voice-sandbox'

    def __init__(self, endpoint, token, allowed_destinations, opener=urlopen):
        parsed=urlparse(endpoint)
        if not token: raise VoiceSandboxError('VOICE_SANDBOX_TOKEN ausente')
        if parsed.scheme not in {'http','https'} or not parsed.hostname: raise VoiceSandboxError('Endpoint inválido')
        if parsed.scheme=='http' and parsed.hostname not in {'127.0.0.1','localhost'}: raise VoiceSandboxError('HTTP só em loopback')
        if parsed.scheme=='https' and not any(x in parsed.hostname.lower() for x in ('sandbox','test')): raise VoiceSandboxError('Endpoint deve identificar sandbox/test')
        if not allowed_destinations or any(not x.upper().startswith(('TEST-','SANDBOX-')) for x in allowed_destinations): raise VoiceSandboxError('Allowlist aceita somente TEST-/SANDBOX-')
        self.endpoint=endpoint;self.token=token;self.allowed=allowed_destinations;self.opener=opener

    def call(self,destination,script,idempotency_key):
        if destination not in self.allowed: raise VoiceSandboxError('Destino fora da allowlist')
        validate_automation_disclosure(script)
        if not idempotency_key or len(idempotency_key)>100: raise VoiceSandboxError('Idempotência inválida')
        payload={'to':destination,'script':script,'automation_disclosed':True,'sandbox':True}
        encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
        req=Request(self.endpoint,data=encoded,headers={'Authorization':f'Bearer {self.token}','Content-Type':'application/json','Idempotency-Key':idempotency_key,'X-AITrack-Environment':'sandbox'},method='POST')
        try:
            with self.opener(req,timeout=10) as response:
                status=response.status;raw=response.read(65537)
                if len(raw)>65536:raise VoiceSandboxError('Resposta acima de 64 KiB')
                value=json.loads(raw.decode())
        except Exception as exc:raise VoiceSandboxError('Falha no provedor de voz sandbox') from exc
        call_id=str(value.get('call_id') or '').strip()
        if status not in range(200,300) or not call_id or value.get('sandbox') is not True:raise VoiceSandboxError('Recibo de voz inválido')
        return VoiceReceipt(self.provider_code,call_id,hashlib.sha256(destination.encode()).hexdigest(),hashlib.sha256(script.encode()).hexdigest(),hashlib.sha256(encoded).hexdigest(),status,{'call_id':call_id,'status':value.get('status','accepted'),'sandbox':True})


def dispatch_voice_action(public_id,provider):
    conn=get_connection();cursor=conn.cursor(dictionary=True)
    try:
        conn.start_transaction();cursor.execute("SELECT * FROM monitoramento.action_queue WHERE public_id=%s FOR UPDATE",(public_id,));action=cursor.fetchone()
        if not action:raise LookupError('Ação não encontrada')
        cursor.execute("SELECT * FROM monitoramento.voice_dispatch_receipts WHERE action_id=%s",(action['id'],));existing=cursor.fetchone()
        if existing:conn.commit();existing['idempotent_replay']=True;return existing
        if action['action_type']!='call_owner' or action['status'] not in {'pending','approved'}:raise ValueError('Ação de voz não executável')
        payload=json.loads(action['payload_json']);version_id=payload.get('script_version_id');variables=payload.get('variables',{})
        cursor.execute("SELECT * FROM monitoramento.message_template_versions WHERE id=%s FOR UPDATE",(version_id,));template=cursor.fetchone()
        if not template or template['status']!='approved':raise ValueError('Roteiro aprovado obrigatório')
        script=render_body(template['body'],json.loads(template['variable_schema_json']),variables);validate_automation_disclosure(script)
        claim=transition_action(public_id,'claim',{'expected_version':action['version'],'idempotency_key':f'{action["idempotency_key"]}:voice:claim','actor_type':'system','actor_id':'voice-sandbox','worker_id':'voice-sandbox','lease_seconds':30},connection=conn)
        try:receipt=provider.call(action['target_ref'],script,action['public_id'])
        except VoiceSandboxError as exc:
            transition_action(public_id,'fail',{'expected_version':claim['version'],'idempotency_key':f'{action["idempotency_key"]}:voice:failed','actor_type':'provider','actor_id':provider.provider_code,'error_code':exc.code,'error_message':str(exc)},connection=conn);conn.commit();raise
        cursor.execute("""INSERT INTO monitoramento.voice_dispatch_receipts(action_id,script_version_id,provider_code,provider_call_id,destination_hash,script_sha256,request_sha256,automation_disclosed,http_status,response_json) VALUES(%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s)""",(action['id'],version_id,receipt.provider_code,receipt.provider_call_id,receipt.destination_hash,receipt.script_sha256,receipt.request_sha256,receipt.http_status,json.dumps(receipt.response,separators=(',',':'),sort_keys=True)))
        transition_action(public_id,'mark_sent',{'expected_version':claim['version'],'idempotency_key':f'{action["idempotency_key"]}:voice:sent','actor_type':'provider','actor_id':provider.provider_code},connection=conn)
        cursor.execute("SELECT * FROM monitoramento.voice_dispatch_receipts WHERE action_id=%s",(action['id'],));result=cursor.fetchone();conn.commit();result['idempotent_replay']=False;return result
    except Exception:
        if conn.in_transaction:conn.rollback()
        raise
    finally:cursor.close();conn.close()


def provider_from_environment(environ=os.environ):
    allowed={x.strip() for x in environ.get('VOICE_SANDBOX_DESTINATIONS','').split(',') if x.strip()}
    return SandboxVoiceProvider(environ.get('VOICE_SANDBOX_URL',''),environ.get('VOICE_SANDBOX_TOKEN',''),allowed)
