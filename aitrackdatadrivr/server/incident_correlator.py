"""Correlação idempotente de episódios comportamentais com incidentes."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Optional

from .incident_sla import SLA_SECONDS, deadline_for


VALID_SOURCES = {'tracker', 'dirijabem'}
VALID_SEVERITIES = {'low', 'medium', 'high', 'critical'}
EVENT_TITLES = {
    'harsh_accel': 'Aceleração brusca detectada',
    'harsh_brake': 'Frenagem brusca detectada',
    'speeding': 'Excesso de velocidade detectado',
    'sharp_turn': 'Curva brusca detectada',
}


def _bounded_key(prefix: str, value: str, maximum: int) -> str:
    candidate = f'{prefix}:{value}'
    if len(candidate) <= maximum:
        return candidate
    digest = hashlib.sha256(candidate.encode('utf-8')).hexdigest()
    return f'{prefix}:{digest}'


def _event_timestamp(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError as exc:
            raise ValueError('timestamp do episódio inválido') from exc
    raise ValueError('timestamp do episódio é obrigatório')


def _resolve_vehicle(cursor, event: Dict, source: str) -> Optional[Dict]:
    if source == 'tracker':
        identity = str(event.get('device_id') or '').strip()
        if not identity:
            raise ValueError('Episódio Tracker exige device_id')
        cursor.execute(
            "SELECT v.id, vi.valor_externo AS device_id, NULL AS codusu "
            "FROM monitoramento.veiculo_identidades vi "
            "JOIN monitoramento.veiculos v ON v.id = vi.vehicle_id "
            "WHERE vi.fonte_codigo = 'tracker' "
            "AND vi.tipo_identidade = 'device_id' "
            "AND vi.valor_externo = %s AND vi.ativo = TRUE "
            "AND v.ativo = TRUE AND v.merged_into_id IS NULL LIMIT 2",
            (identity,),
        )
    else:
        codusu = event.get('codusu')
        if not isinstance(codusu, int) or isinstance(codusu, bool) or codusu <= 0:
            raise ValueError('Episódio Dirija Bem exige codusu positivo')
        plate = ''.join(
            char for char in str(event.get('placa') or '').upper()
            if char.isalnum()
        )
        plate_filter = 'AND v.placa = %s' if plate else ''
        params = (str(codusu), plate) if plate else (str(codusu),)
        cursor.execute(f"""
            SELECT DISTINCT v.id, NULL AS device_id,
                   CAST(mi.valor_externo AS UNSIGNED) AS codusu
              FROM monitoramento.motorista_identidades mi
              JOIN monitoramento.veiculo_motorista_vinculos vmv
                ON vmv.driver_id = mi.driver_id
              JOIN monitoramento.veiculos v ON v.id = vmv.vehicle_id
             WHERE mi.fonte_codigo = 'dirijabem'
               AND mi.tipo_identidade = 'user_id'
               AND mi.valor_externo = %s
               AND mi.ativo = TRUE AND v.ativo = TRUE
               AND v.merged_into_id IS NULL
               {plate_filter}
             LIMIT 2
        """, params)

    rows = cursor.fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        raise ValueError('Identidade veicular ambígua')
    return rows[0]


def correlate_episode(
    cursor,
    event: Dict,
    tracker_event_id: Optional[int] = None,
    score_after: Optional[float] = None,
) -> Dict:
    """Cria ou enriquece um incidente usando a transação do evento chamador."""
    if not isinstance(event, dict):
        raise ValueError('event deve ser um objeto')
    source = event.get('source', 'tracker')
    if source not in VALID_SOURCES:
        raise ValueError('source do episódio inválido')

    episode_id = str(event.get('episode_id') or '').strip()
    if not episode_id:
        return {'status': 'ignored', 'reason': 'missing_episode_id'}
    event_type = str(event.get('type') or '').strip()
    if not event_type or len(event_type) > 50:
        raise ValueError('type deve ter entre 1 e 50 caracteres')
    severity = event.get('severity', 'medium')
    if severity not in VALID_SEVERITIES:
        raise ValueError('severity do episódio inválida')

    vehicle = _resolve_vehicle(cursor, event, source)
    if vehicle is None:
        return {'status': 'ignored', 'reason': 'vehicle_identity_not_found'}

    observed_at = _event_timestamp(event.get('timestamp'))
    correlation_group = str(event.get('correlation_group') or episode_id).strip()
    correlation_key = _bounded_key(f'behavior:{vehicle["id"]}', correlation_group, 150)
    stored_episode_id = episode_id if len(episode_id) <= 64 else hashlib.sha256(
        episode_id.encode('utf-8')
    ).hexdigest()
    title = EVENT_TITLES.get(event_type, f'Evento comportamental: {event_type}')[:200]
    risk_score = None if score_after is None else max(0.0, min(100.0, 100.0 - float(score_after)))
    context_snapshot = json.dumps(event, default=str, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO monitoramento.incidents
            (correlation_key, vehicle_id, origin_episode_id, incident_type,
             title, summary, status, severity, risk_score, primary_source,
             latitude, longitude, position_observed_at, context_snapshot,
             opened_at, sla_due_at, event_count)
        VALUES (%s, %s, %s, %s, %s, %s, 'new', %s, %s, %s,
                %s, %s, %s, %s, %s, %s, 0)
        ON DUPLICATE KEY UPDATE correlation_key = VALUES(correlation_key)
    """, (
        correlation_key, vehicle['id'], stored_episode_id, event_type, title,
        f'Episódio {event_type} recebido de {source}.', severity, risk_score, source,
        event.get('lat'), event.get('lon'), observed_at, context_snapshot, observed_at,
        deadline_for(severity),
    ))
    incident_created = cursor.rowcount == 1
    cursor.execute(
        'SELECT id, primary_source FROM monitoramento.incidents '
        'WHERE correlation_key = %s FOR UPDATE',
        (correlation_key,),
    )
    incident = cursor.fetchone()
    if not incident:
        raise RuntimeError('Incidente correlacionado não foi localizado')

    source_record_ref = event.get('source_record_id')
    if source_record_ref is None and source == 'tracker':
        source_record_ref = tracker_event_id
    evidence_ref = str(source_record_ref or episode_id)
    idempotency_key = _bounded_key(
        f'incident:{incident["id"]}:evidence:{source}', evidence_ref, 150
    )
    timeline_event_id = tracker_event_id if source == 'tracker' else None
    details = json.dumps({
        'source': source,
        'source_record_id': source_record_ref,
        'episode_id': episode_id,
        'event_type': event_type,
        'severity': severity,
        'observed_at': observed_at,
    }, default=str, ensure_ascii=False)
    cursor.execute("""
        INSERT INTO monitoramento.incident_timeline
            (incident_id, idempotency_key, entry_type, actor_type,
             actor_id, actor_name, from_status, to_status, summary,
             details, event_id, event_source, evidence_type, evidence_ref,
             correlation_id, occurred_at)
        VALUES (%s, %s, 'evidence_added', 'integration', %s, %s,
                NULL, NULL, %s, %s, %s, %s, 'behavior_episode', %s, %s, %s)
        ON DUPLICATE KEY UPDATE id = id
    """, (
        incident['id'], idempotency_key, source, f'Integração {source}',
        f'Evidência {event_type} recebida de {source}', details,
        timeline_event_id, source, evidence_ref[:150], correlation_group[:100],
        observed_at,
    ))
    evidence_added = cursor.rowcount == 1

    if evidence_added:
        next_source = source if incident['primary_source'] == source else 'fused'
        cursor.execute("""
            UPDATE monitoramento.incidents
               SET event_count = event_count + 1,
                   version = version + 1,
                   primary_source = %s,
                   severity = CASE
                       WHEN FIELD(%s, 'low', 'medium', 'high', 'critical')
                          > FIELD(severity, 'low', 'medium', 'high', 'critical')
                       THEN %s ELSE severity END,
                   risk_score = CASE
                       WHEN %s IS NULL THEN risk_score
                       WHEN risk_score IS NULL OR %s > risk_score THEN %s
                       ELSE risk_score END,
                   sla_due_at = LEAST(
                       COALESCE(sla_due_at, CURRENT_TIMESTAMP(6) + INTERVAL %s SECOND),
                       CURRENT_TIMESTAMP(6) + INTERVAL %s SECOND
                   ),
                   updated_at = CURRENT_TIMESTAMP(6)
             WHERE id = %s
        """, (
            next_source, severity, severity, risk_score, risk_score, risk_score,
            SLA_SECONDS[severity], SLA_SECONDS[severity],
            incident['id'],
        ))

    return {
        'status': 'correlated',
        'incident_id': int(incident['id']),
        'incident_created': incident_created,
        'evidence_added': evidence_added,
        'correlation_key': correlation_key,
    }
