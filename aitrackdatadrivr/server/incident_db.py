"""Consultas e transições atômicas de incidentes operacionais."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .monitor_db import get_connection
from .identity_db import configured_read_mode
from .incident_state_machine import FALSE_NEGATIVE_REASONS, plan_transition
from .incident_sla import deadline_for, enrich_sla


class IncidentNotFound(Exception):
    pass


class IncidentConflict(Exception):
    pass


INCIDENT_SELECT = """
    SELECT i.*,
           (SELECT vi.valor_externo
              FROM monitoramento.veiculo_identidades vi
             WHERE vi.vehicle_id = v.id AND vi.fonte_codigo = 'tracker'
               AND vi.tipo_identidade = 'device_id' AND vi.ativo = TRUE
             ORDER BY vi.principal DESC, vi.id LIMIT 1) AS device_id,
           (SELECT CAST(mi.valor_externo AS UNSIGNED)
              FROM monitoramento.veiculo_motorista_vinculos vmv
              JOIN monitoramento.motorista_identidades mi
                ON mi.driver_id = vmv.driver_id
               AND mi.fonte_codigo = 'dirijabem'
               AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
             WHERE vmv.vehicle_id = v.id
             ORDER BY COALESCE(vmv.valido_ate, '9999-12-31') DESC,
                      vmv.valido_desde DESC LIMIT 1) AS codusu,
           v.placa, v.descricao AS vehicle_name,
           CASE
             WHEN EXISTS (
               SELECT 1 FROM monitoramento.veiculo_identidades vi
                WHERE vi.vehicle_id = v.id AND vi.fonte_codigo = 'tracker'
                  AND vi.ativo = TRUE
             ) AND EXISTS (
               SELECT 1 FROM monitoramento.veiculo_motorista_vinculos vmv
                WHERE vmv.vehicle_id = v.id AND vmv.fonte_codigo = 'dirijabem'
             ) THEN 'both'
             WHEN EXISTS (
               SELECT 1 FROM monitoramento.veiculo_identidades vi
                WHERE vi.vehicle_id = v.id AND vi.fonte_codigo = 'tracker'
                  AND vi.ativo = TRUE
             ) THEN 'tracker_only' ELSE 'app_only'
           END AS vehicle_identity_type,
           m.nome AS monitor_name,
           (SELECT COUNT(*)
              FROM monitoramento.incident_timeline it
             WHERE it.incident_id = i.id) AS timeline_entries
      FROM monitoramento.incidents i
      JOIN monitoramento.veiculos v ON v.id = i.vehicle_id
 LEFT JOIN monitoramento.monitores m ON m.id = i.monitor_id
"""


def serialize_record(record: Dict) -> Dict:
    """Converte tipos do conector MySQL para um contrato JSON estável."""
    serialized = {}
    for key, value in record.items():
        if isinstance(value, (datetime, date)):
            serialized[key] = value.isoformat()
        elif isinstance(value, Decimal):
            serialized[key] = float(value)
        elif key in {'context_snapshot', 'details'} and isinstance(value, str):
            try:
                serialized[key] = json.loads(value)
            except json.JSONDecodeError:
                serialized[key] = None
        elif key == 'false_positive' and value is not None:
            serialized[key] = bool(value)
        else:
            serialized[key] = value
    return serialized


def _where_clause(filters: Dict) -> Tuple[str, List]:
    clauses = []
    params: List = []
    field_map = {
        'status': 'i.status',
        'severity': 'i.severity',
        'primary_source': 'i.primary_source',
        'vehicle_id': 'i.vehicle_id',
        'monitor_id': 'i.monitor_id',
        'assigned_to': 'i.assigned_to',
    }
    for key, column in field_map.items():
        if filters.get(key) is not None:
            clauses.append(f'{column} = %s')
            params.append(filters[key])
    if filters.get('open_only'):
        clauses.append("i.status NOT IN ('resolved', 'closed')")
    return (' WHERE ' + ' AND '.join(clauses) if clauses else ''), params


def list_incidents(filters: Dict, limit: int, offset: int) -> Tuple[List[Dict], int]:
    where_sql, params = _where_clause(filters)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            f'SELECT COUNT(*) AS total FROM monitoramento.incidents i{where_sql}',
            tuple(params),
        )
        total = int(cursor.fetchone()['total'])
        cursor.execute(
            INCIDENT_SELECT + where_sql
            + " ORDER BY CASE"
              " WHEN i.status NOT IN ('resolved', 'closed') AND i.sla_due_at < CURRENT_TIMESTAMP(6) THEN 0"
              " WHEN i.status = 'escalated' THEN 1 ELSE 2 END,"
              " i.sla_due_at IS NULL, i.sla_due_at ASC, i.updated_at DESC, i.id DESC"
              " LIMIT %s OFFSET %s",
            tuple([*params, limit, offset]),
        )
        return [serialize_record(enrich_sla(row)) for row in cursor.fetchall()], total
    finally:
        cursor.close()
        conn.close()


def get_incident(incident_id: int, timeline_limit: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(INCIDENT_SELECT + ' WHERE i.id = %s', (incident_id,))
        incident = cursor.fetchone()
        if not incident:
            return None

        cursor.execute(
            'SELECT COUNT(*) AS total FROM monitoramento.incident_timeline WHERE incident_id = %s',
            (incident_id,),
        )
        timeline_total = int(cursor.fetchone()['total'])
        cursor.execute("""
            SELECT id, incident_id, idempotency_key, entry_type,
                   actor_type, actor_id, actor_name, from_status, to_status,
                   summary, details, event_id, evidence_type, evidence_ref,
                   correlation_id, causation_id, visibility,
                   occurred_at, recorded_at
              FROM monitoramento.incident_timeline
             WHERE incident_id = %s
             ORDER BY occurred_at DESC, id DESC
             LIMIT %s
        """, (incident_id, timeline_limit))
        timeline = [serialize_record(row) for row in reversed(cursor.fetchall())]
        result = serialize_record(enrich_sla(incident))
        result['timeline'] = timeline
        result['timeline_total'] = timeline_total
        result['timeline_truncated'] = timeline_total > len(timeline)
        return result
    finally:
        cursor.close()
        conn.close()


def transition_incident(
    incident_id: int,
    command: str,
    payload: Dict,
    actor: Dict,
    expected_version: int,
    idempotency_key: str,
    connection=None,
) -> Dict:
    """Altera estado e grava timeline atomicamente com concorrência otimista."""
    if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
        raise ValueError('expected_version deve ser inteiro positivo')
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key.strip()) <= 150:
        raise ValueError('idempotency_key deve ter entre 1 e 150 caracteres')
    if not isinstance(actor, dict) or actor.get('type') not in {
        'system', 'human', 'agent', 'integration',
    }:
        raise ValueError('actor.type inválido')
    if not actor.get('id') and not actor.get('name'):
        raise ValueError('Ator deve possuir id ou nome')
    if len(str(actor.get('id') or '')) > 100 or len(str(actor.get('name') or '')) > 150:
        raise ValueError('Identificação do ator excede o limite')
    if not isinstance(payload, dict):
        raise ValueError('payload deve ser um objeto')
    if len(str(payload.get('correlation_id') or '')) > 100:
        raise ValueError('correlation_id deve ter no máximo 100 caracteres')

    idempotency_key = idempotency_key.strip()
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT * FROM monitoramento.incidents WHERE id = %s FOR UPDATE',
            (incident_id,),
        )
        incident = cursor.fetchone()
        if not incident:
            raise IncidentNotFound()
        # O lock do incidente vem antes da consulta de idempotência. Assim,
        # retries simultâneos aguardam a primeira transação e enxergam sua
        # timeline, em vez de falharem artificialmente por versão obsoleta.
        cursor.execute(
            'SELECT incident_id FROM monitoramento.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            if int(replay['incident_id']) != incident_id:
                raise IncidentConflict('Chave de idempotência pertence a outro incidente')
            result = serialize_record(incident)
            result['idempotent_replay'] = True
            return result
        if int(incident['version']) != expected_version:
            raise IncidentConflict(
                f'Versão divergente: atual={incident["version"]}, esperada={expected_version}'
            )

        plan = plan_transition(incident, command, payload)
        if command == 'resolve':
            plan['updates']['classified_by'] = str(actor.get('id') or '')[:100]
        assignments = [f'{field} = %s' for field in plan['updates']]
        values = list(plan['updates'].values())
        assignments.extend(['version = version + 1', 'updated_at = CURRENT_TIMESTAMP(6)'])
        cursor.execute(
            f'UPDATE monitoramento.incidents SET {", ".join(assignments)} '
            'WHERE id = %s AND version = %s',
            tuple([*values, incident_id, expected_version]),
        )
        if cursor.rowcount != 1:
            raise IncidentConflict('Incidente foi alterado por outro processo')

        details = {
            'command': command,
            'expected_version': expected_version,
            'new_version': expected_version + 1,
            **{key: value for key, value in payload.items() if key != 'resolution_notes'},
        }
        cursor.execute("""
            INSERT INTO monitoramento.incident_timeline
                (incident_id, idempotency_key, entry_type, actor_type,
                 actor_id, actor_name, from_status, to_status,
                 summary, details, correlation_id, occurred_at)
            VALUES (%s, %s, 'status_changed', %s, %s, %s, %s, %s,
                    %s, %s, %s, CURRENT_TIMESTAMP(6))
        """, (
            incident_id, idempotency_key, actor['type'], actor.get('id'),
            actor.get('name'), plan['from_status'], plan['to_status'],
            plan['summary'], json.dumps(details, default=str),
            payload.get('correlation_id'),
        ))
        cursor.execute('SELECT * FROM monitoramento.incidents WHERE id = %s', (incident_id,))
        result = serialize_record(cursor.fetchone())
        result['idempotent_replay'] = False
        if owns_connection:
            conn.commit()
        return result
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()


def add_incident_comment(
    incident_id: int,
    comment: str,
    actor: Dict,
    expected_version: int,
    idempotency_key: str,
    connection=None,
) -> Dict:
    """Acrescenta comentário auditável e atualiza a versão atomicamente."""
    comment = str(comment or '').strip()
    if not 2 <= len(comment) <= 2000:
        raise ValueError('Comentário deve ter entre 2 e 2000 caracteres')
    if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
        raise ValueError('expected_version deve ser inteiro positivo')
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key.strip()) <= 150:
        raise ValueError('idempotency_key deve ter entre 1 e 150 caracteres')
    if not isinstance(actor, dict) or actor.get('type') != 'human':
        raise ValueError('Comentário operacional exige ator humano')
    if not actor.get('id') or not actor.get('name'):
        raise ValueError('Ator deve possuir id e nome')

    idempotency_key = idempotency_key.strip()
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM monitoramento.incidents WHERE id = %s FOR UPDATE', (incident_id,))
        incident = cursor.fetchone()
        if not incident:
            raise IncidentNotFound()
        cursor.execute(
            'SELECT incident_id FROM monitoramento.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            if int(replay['incident_id']) != incident_id:
                raise IncidentConflict('Chave de idempotência pertence a outro incidente')
            result = serialize_record(incident)
            result['idempotent_replay'] = True
            return result
        if int(incident['version']) != expected_version:
            raise IncidentConflict(
                f'Versão divergente: atual={incident["version"]}, esperada={expected_version}'
            )

        cursor.execute(
            'UPDATE monitoramento.incidents SET version = version + 1, '
            'updated_at = CURRENT_TIMESTAMP(6) WHERE id = %s AND version = %s',
            (incident_id, expected_version),
        )
        if cursor.rowcount != 1:
            raise IncidentConflict('Incidente foi alterado por outro processo')
        cursor.execute("""
            INSERT INTO monitoramento.incident_timeline
                (incident_id, idempotency_key, entry_type, actor_type,
                 actor_id, actor_name, summary, details, occurred_at)
            VALUES (%s, %s, 'comment', 'human', %s, %s, %s, %s,
                    CURRENT_TIMESTAMP(6))
        """, (
            incident_id, idempotency_key, str(actor['id'])[:100],
            str(actor['name'])[:150], comment[:300],
            json.dumps({'comment': comment}, ensure_ascii=False),
        ))
        cursor.execute('SELECT * FROM monitoramento.incidents WHERE id = %s', (incident_id,))
        result = serialize_record(cursor.fetchone())
        result['idempotent_replay'] = False
        if owns_connection:
            conn.commit()
        return result
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()


def _resolve_input_vehicle_id(cursor, provided_id: int) -> int:
    """Converte ID legado da UI ou confirma ID canônico após a virada."""
    if configured_read_mode() == 'operational':
        cursor.execute(
            'SELECT id FROM monitoramento.veiculos '
            'WHERE id = %s AND ativo = TRUE AND merged_into_id IS NULL',
            (provided_id,),
        )
        vehicle = cursor.fetchone()
        if not vehicle:
            raise ValueError('Veículo operacional ativo não encontrado')
        return int(vehicle['id'])

    cursor.execute(
        'SELECT device_id, placa FROM tracker.veiculo_unificado '
        'WHERE id = %s AND ativo = TRUE',
        (provided_id,),
    )
    legacy = cursor.fetchone()
    if legacy and legacy.get('device_id'):
        cursor.execute("""
            SELECT vehicle_id AS id
              FROM monitoramento.veiculo_identidades
             WHERE fonte_codigo = 'tracker'
               AND tipo_identidade = 'device_id'
               AND valor_externo = %s AND ativo = TRUE
        """, (legacy['device_id'],))
    elif legacy and legacy.get('placa'):
        normalized_plate = ''.join(
            char for char in str(legacy['placa']).upper() if char.isalnum()
        )
        cursor.execute(
            'SELECT id FROM monitoramento.veiculos '
            'WHERE placa = %s AND ativo = TRUE AND merged_into_id IS NULL',
            (normalized_plate,),
        )
    else:
        raise ValueError('Veículo unificado ativo não encontrado')
    matches = cursor.fetchall()
    if len(matches) != 1:
        raise ValueError('Identidade operacional do veículo não é única')
    return int(matches[0]['id'])


def create_false_negative(data: Dict, actor: Dict, idempotency_key: str, connection=None) -> Dict:
    """Registra fato real que não foi detectado automaticamente."""
    vehicle_id = data.get('vehicle_id')
    if not isinstance(vehicle_id, int) or isinstance(vehicle_id, bool) or vehicle_id < 1:
        raise ValueError('vehicle_id deve ser inteiro positivo')
    incident_type = str(data.get('incident_type') or '').strip()
    title = str(data.get('title') or '').strip()
    notes = str(data.get('notes') or '').strip()
    severity = data.get('severity')
    reason = data.get('classification_reason')
    occurred_at = data.get('occurred_at')
    if not 1 <= len(incident_type) <= 50:
        raise ValueError('incident_type deve ter entre 1 e 50 caracteres')
    if not 3 <= len(title) <= 200:
        raise ValueError('title deve ter entre 3 e 200 caracteres')
    if not 10 <= len(notes) <= 4000:
        raise ValueError('notes deve ter entre 10 e 4000 caracteres')
    if severity not in {'low', 'medium', 'high', 'critical'}:
        raise ValueError('severity inválida')
    if reason not in FALSE_NEGATIVE_REASONS:
        raise ValueError('Motivo de falso negativo inválido')
    if not isinstance(occurred_at, datetime):
        raise ValueError('occurred_at deve ser datetime')
    if not isinstance(actor, dict) or actor.get('type') != 'human' or not actor.get('id') or not actor.get('name'):
        raise ValueError('Registro de falso negativo exige ator humano identificado')
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key.strip()) <= 150:
        raise ValueError('idempotency_key deve ter entre 1 e 150 caracteres')

    idempotency_key = idempotency_key.strip()
    correlation_key = f'false-negative:{idempotency_key}'
    if len(correlation_key) > 150:
        digest = hashlib.sha256(correlation_key.encode('utf-8')).hexdigest()
        correlation_key = f'false-negative:{digest}'
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT incident_id FROM monitoramento.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            cursor.execute(
                'SELECT * FROM monitoramento.incidents WHERE id = %s',
                (replay['incident_id'],),
            )
            result = serialize_record(cursor.fetchone())
            result['idempotent_replay'] = True
            return result

        operational_vehicle_id = _resolve_input_vehicle_id(cursor, vehicle_id)
        cursor.execute("""
            INSERT INTO monitoramento.incidents
                (correlation_key, vehicle_id, legacy_vehicle_id,
                 incident_type, title, summary,
                 status, severity, primary_source, opened_at, triaged_at,
                 detection_outcome, classification_reason, classified_by,
                 classified_at, sla_due_at, version)
            VALUES (%s, %s, %s, %s, %s, %s, 'triage', %s, 'system', %s,
                    CURRENT_TIMESTAMP(6), 'false_negative', %s, %s,
                    CURRENT_TIMESTAMP(6), %s, 1)
        """, (
            correlation_key, operational_vehicle_id, vehicle_id,
            incident_type, title, notes, severity,
            occurred_at, reason, str(actor['id'])[:100], deadline_for(severity),
        ))
        incident_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO monitoramento.incident_timeline
                (incident_id, idempotency_key, entry_type, actor_type,
                 actor_id, actor_name, summary, details, occurred_at)
            VALUES (%s, %s, 'false_negative_reported', 'human', %s, %s,
                    %s, %s, %s)
        """, (
            incident_id, idempotency_key, str(actor['id'])[:100],
            str(actor['name'])[:150], f'Falso negativo reportado: {title}'[:300],
            json.dumps({
                'classification_reason': reason,
                'notes': notes,
                'incident_type': incident_type,
                'severity': severity,
            }, ensure_ascii=False), occurred_at,
        ))
        cursor.execute('SELECT * FROM monitoramento.incidents WHERE id = %s', (incident_id,))
        result = serialize_record(cursor.fetchone())
        result['idempotent_replay'] = False
        if owns_connection:
            conn.commit()
        return result
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()
