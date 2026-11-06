"""Consultas e transições atômicas de incidentes operacionais."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .monitor_db import get_connection
from .incident_state_machine import FALSE_NEGATIVE_REASONS, plan_transition


class IncidentNotFound(Exception):
    pass


class IncidentConflict(Exception):
    pass


INCIDENT_SELECT = """
    SELECT i.*,
           vu.device_id, vu.codusu, vu.placa, vu.descricao AS vehicle_name,
           vu.tipo AS vehicle_identity_type,
           m.nome AS monitor_name,
           (SELECT COUNT(*)
              FROM tracker.incident_timeline it
             WHERE it.incident_id = i.id) AS timeline_entries
      FROM tracker.incidents i
      JOIN tracker.veiculo_unificado vu ON vu.id = i.vehicle_id
 LEFT JOIN tracker.monitores m ON m.id = i.monitor_id
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
            f'SELECT COUNT(*) AS total FROM tracker.incidents i{where_sql}',
            tuple(params),
        )
        total = int(cursor.fetchone()['total'])
        cursor.execute(
            INCIDENT_SELECT + where_sql
            + ' ORDER BY i.updated_at DESC, i.id DESC LIMIT %s OFFSET %s',
            tuple([*params, limit, offset]),
        )
        return [serialize_record(row) for row in cursor.fetchall()], total
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
            'SELECT COUNT(*) AS total FROM tracker.incident_timeline WHERE incident_id = %s',
            (incident_id,),
        )
        timeline_total = int(cursor.fetchone()['total'])
        cursor.execute("""
            SELECT id, incident_id, idempotency_key, entry_type,
                   actor_type, actor_id, actor_name, from_status, to_status,
                   summary, details, event_id, evidence_type, evidence_ref,
                   correlation_id, causation_id, visibility,
                   occurred_at, recorded_at
              FROM tracker.incident_timeline
             WHERE incident_id = %s
             ORDER BY occurred_at DESC, id DESC
             LIMIT %s
        """, (incident_id, timeline_limit))
        timeline = [serialize_record(row) for row in reversed(cursor.fetchall())]
        result = serialize_record(incident)
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
            'SELECT incident_id FROM tracker.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            if int(replay['incident_id']) != incident_id:
                raise IncidentConflict('Chave de idempotência pertence a outro incidente')
            cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (incident_id,))
            result = serialize_record(cursor.fetchone())
            result['idempotent_replay'] = True
            return result

        cursor.execute(
            'SELECT * FROM tracker.incidents WHERE id = %s FOR UPDATE',
            (incident_id,),
        )
        incident = cursor.fetchone()
        if not incident:
            raise IncidentNotFound()
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
            f'UPDATE tracker.incidents SET {", ".join(assignments)} '
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
            INSERT INTO tracker.incident_timeline
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
        cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (incident_id,))
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
        cursor.execute(
            'SELECT incident_id FROM tracker.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            if int(replay['incident_id']) != incident_id:
                raise IncidentConflict('Chave de idempotência pertence a outro incidente')
            cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (incident_id,))
            result = serialize_record(cursor.fetchone())
            result['idempotent_replay'] = True
            return result

        cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s FOR UPDATE', (incident_id,))
        incident = cursor.fetchone()
        if not incident:
            raise IncidentNotFound()
        if int(incident['version']) != expected_version:
            raise IncidentConflict(
                f'Versão divergente: atual={incident["version"]}, esperada={expected_version}'
            )

        cursor.execute(
            'UPDATE tracker.incidents SET version = version + 1, '
            'updated_at = CURRENT_TIMESTAMP(6) WHERE id = %s AND version = %s',
            (incident_id, expected_version),
        )
        if cursor.rowcount != 1:
            raise IncidentConflict('Incidente foi alterado por outro processo')
        cursor.execute("""
            INSERT INTO tracker.incident_timeline
                (incident_id, idempotency_key, entry_type, actor_type,
                 actor_id, actor_name, summary, details, occurred_at)
            VALUES (%s, %s, 'comment', 'human', %s, %s, %s, %s,
                    CURRENT_TIMESTAMP(6))
        """, (
            incident_id, idempotency_key, str(actor['id'])[:100],
            str(actor['name'])[:150], comment[:300],
            json.dumps({'comment': comment}, ensure_ascii=False),
        ))
        cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (incident_id,))
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
            'SELECT incident_id FROM tracker.incident_timeline WHERE idempotency_key = %s',
            (idempotency_key,),
        )
        replay = cursor.fetchone()
        if replay:
            cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (replay['incident_id'],))
            result = serialize_record(cursor.fetchone())
            result['idempotent_replay'] = True
            return result

        cursor.execute(
            'SELECT id FROM tracker.veiculo_unificado WHERE id = %s AND ativo = TRUE',
            (vehicle_id,),
        )
        if not cursor.fetchone():
            raise ValueError('Veículo unificado ativo não encontrado')
        cursor.execute("""
            INSERT INTO tracker.incidents
                (correlation_key, vehicle_id, incident_type, title, summary,
                 status, severity, primary_source, opened_at, triaged_at,
                 detection_outcome, classification_reason, classified_by,
                 classified_at, version)
            VALUES (%s, %s, %s, %s, %s, 'triage', %s, 'system', %s,
                    CURRENT_TIMESTAMP(6), 'false_negative', %s, %s,
                    CURRENT_TIMESTAMP(6), 1)
        """, (
            correlation_key, vehicle_id, incident_type, title, notes, severity,
            occurred_at, reason, str(actor['id'])[:100],
        ))
        incident_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO tracker.incident_timeline
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
        cursor.execute('SELECT * FROM tracker.incidents WHERE id = %s', (incident_id,))
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
