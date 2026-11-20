"""Cadastro seguro e resolução determinística de contatos consentidos."""

from datetime import datetime
import hashlib
import json

from .monitor_db import get_connection

ROLES = {'owner', 'manager', 'operations_center'}
CHANNELS = {'sms', 'whatsapp', 'voice', 'email', 'internal'}
SEVERITY_RANK = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}


def validate_destination_ref(value):
    ref = str(value or '').strip()
    if not ref.startswith(('vault:', 'TEST-', 'SANDBOX-', 'internal:')):
        raise ValueError('Destino deve ser referência de cofre, interna ou sandbox')
    if len(ref) > 200:
        raise ValueError('destination_ref acima do limite')
    return ref


def channel_is_eligible(row, now=None):
    now = now or datetime.now()
    return bool(
        row.get('active')
        and row.get('consent_status') == 'granted'
        and row.get('verified_at') is not None
        and row.get('consent_granted_at') is not None
        and row.get('consent_revoked_at') is None
        and (row.get('consent_expires_at') is None or row['consent_expires_at'] > now)
    )


def order_candidates(candidates, incident_severity):
    severity = SEVERITY_RANK.get(incident_severity)
    if severity is None:
        raise ValueError('Severidade inválida')
    eligible = [
        item for item in candidates
        if channel_is_eligible(item)
        and SEVERITY_RANK[item['min_severity']] <= severity
    ]
    return sorted(eligible, key=lambda item: (item['step_order'], item['priority'], item['channel_id']))


def register_contact(payload):
    role = payload.get('role'); channel = payload.get('channel')
    display = str(payload.get('display_name') or '').strip()
    actor = str(payload.get('actor_id') or '').strip()
    reason = str(payload.get('reason') or '').strip()
    destination = validate_destination_ref(payload.get('destination_ref'))
    if role not in ROLES or channel not in CHANNELS or not display or not actor or not reason:
        raise ValueError('papel, canal, nome, ator e motivo obrigatórios')
    consent = payload.get('consent_status', 'pending')
    if consent not in {'pending', 'granted', 'revoked', 'expired'}:
        raise ValueError('consent_status inválido')
    digest = hashlib.sha256(destination.encode()).hexdigest()
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("""INSERT INTO monitoramento.contact_profiles
          (public_id,owner_ref,vehicle_id,role,display_name) VALUES(UUID(),%s,%s,%s,%s)""",
          (payload.get('owner_ref'), payload.get('vehicle_id'), role, display))
        contact_id = cursor.lastrowid
        cursor.execute("""INSERT INTO monitoramento.contact_channels
          (contact_id,channel,destination_ref,destination_hash,priority,verified_at,
           consent_status,consent_scope,consent_source,consent_granted_at)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
            contact_id, channel, destination, digest, payload.get('priority', 100),
            payload.get('verified_at'), consent, payload.get('consent_scope', 'vehicle-safety'),
            payload.get('consent_source', 'operator'), payload.get('consent_granted_at'),
        ))
        snapshot = {'role': role, 'channel': channel, 'destination_hash': digest, 'consent_status': consent}
        cursor.execute("INSERT INTO monitoramento.contact_audit(contact_id,event_type,actor_id,reason,snapshot_json) VALUES(%s,'created',%s,%s,%s)",
                       (contact_id, actor, reason, json.dumps(snapshot, separators=(',', ':'), sort_keys=True)))
        conn.commit(); return {'contact_id': contact_id, **snapshot}
    except Exception:
        conn.rollback(); raise
    finally:
        cursor.close(); conn.close()


def resolve_escalation(incident_id, policy_key='default'):
    if not isinstance(incident_id, int) or incident_id < 1:
        raise ValueError('incident_id inválido')
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT vehicle_id,owner_ref,severity FROM monitoramento.incidents WHERE id=%s", (incident_id,))
        incident = cursor.fetchone()
        if not incident: raise LookupError('Incidente não encontrado')
        cursor.execute("""SELECT s.step_order,s.min_severity,s.wait_seconds,
                  c.id contact_id,c.display_name,ch.id channel_id,ch.channel,
                  ch.destination_ref,ch.destination_hash,ch.priority,ch.active,
                  ch.verified_at,ch.consent_status,ch.consent_granted_at,
                  ch.consent_revoked_at,ch.consent_expires_at,p.id policy_version_id,p.version_no
             FROM monitoramento.escalation_policy_versions p
             JOIN monitoramento.escalation_policy_steps s ON s.policy_version_id=p.id
             JOIN monitoramento.contact_profiles c ON c.role=s.contact_role AND c.active=TRUE
             JOIN monitoramento.contact_channels ch ON ch.contact_id=c.id AND ch.channel=s.channel
            WHERE p.policy_key=%s AND p.status='active'
              AND ((c.vehicle_id=%s) OR (c.vehicle_id IS NULL AND c.owner_ref=%s))""",
            (policy_key, incident['vehicle_id'], incident['owner_ref']))
        ordered = order_candidates(cursor.fetchall(), incident['severity'])
        return {'incident_id': incident_id, 'policy_key': policy_key, 'contacts': ordered}
    finally:
        cursor.close(); conn.close()
