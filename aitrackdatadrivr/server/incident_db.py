"""Consultas somente leitura para incidentes e sua timeline."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .monitor_db import get_connection


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
