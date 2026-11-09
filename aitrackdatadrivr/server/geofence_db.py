"""Persistência operacional de cercas e suas versões geométricas."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from .monitor_db import get_connection


class GeofenceNotFound(Exception):
    pass


class GeofenceConflict(Exception):
    pass


class GeofenceArchived(Exception):
    pass


class GeofenceHasActiveAssignments(Exception):
    def __init__(self, count: int):
        self.count = count
        super().__init__(f'Cerca possui {count} atribuição(ões) ativa(s)')


GEOFENCE_SELECT = """
    SELECT g.id, g.public_id, g.nome, g.descricao, g.regra, g.status,
           g.owner_ref, g.criado_por, g.atualizado_por, g.version,
           g.criado_em, g.atualizado_em,
           gv.id AS geometry_version_id, gv.version_number AS geometry_version,
           gv.geometry_type, gv.radius_meters, gv.geometry_hash,
           gv.change_reason, gv.created_by AS geometry_created_by,
           gv.valid_from, gv.valid_to, gv.created_at AS geometry_created_at,
           ST_AsGeoJSON(gv.geometry) AS geometry_geojson,
           (SELECT COUNT(*) FROM monitoramento.geofence_assignments ga
             WHERE ga.geofence_id = g.id AND ga.ativo = TRUE) AS active_assignments
      FROM monitoramento.geofences g
      JOIN monitoramento.geofence_versions gv
        ON gv.geofence_id = g.id
       AND gv.version_number = (
           SELECT MAX(latest.version_number)
             FROM monitoramento.geofence_versions latest
            WHERE latest.geofence_id = g.id
       )
"""


def _serialize(record: Dict) -> Dict:
    result = {}
    for key, value in record.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    geojson = result.pop('geometry_geojson', None)
    if geojson:
        parsed = json.loads(geojson)
        if result['geometry_type'] == 'circle':
            result['geometry'] = {
                'type': 'Circle',
                'center': parsed['coordinates'],
                'radius_meters': result['radius_meters'],
            }
        else:
            result['geometry'] = parsed
    return result


def _where_clause(filters: Dict) -> Tuple[str, List]:
    clauses = []
    params: List = []
    for key, column in (('status', 'g.status'), ('regra', 'g.regra')):
        if filters.get(key):
            clauses.append(f'{column} = %s')
            params.append(filters[key])
    if filters.get('search'):
        clauses.append('(g.nome LIKE %s OR g.descricao LIKE %s)')
        term = f"%{filters['search']}%"
        params.extend((term, term))
    return (' WHERE ' + ' AND '.join(clauses) if clauses else ''), params


def list_geofences(filters: Dict, limit: int, offset: int) -> Tuple[List[Dict], int]:
    where_sql, params = _where_clause(filters)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            f'SELECT COUNT(*) AS total FROM monitoramento.geofences g{where_sql}',
            tuple(params),
        )
        total = int(cursor.fetchone()['total'])
        cursor.execute(
            GEOFENCE_SELECT + where_sql
            + ' ORDER BY g.atualizado_em DESC, g.id DESC LIMIT %s OFFSET %s',
            tuple(params + [limit, offset]),
        )
        return [_serialize(row) for row in cursor.fetchall()], total
    finally:
        cursor.close()
        conn.close()


def get_geofence(reference: str) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if reference.isdigit():
            clause, parameter = 'g.id = %s', int(reference)
        else:
            clause, parameter = 'g.public_id = %s', reference
        cursor.execute(GEOFENCE_SELECT + f' WHERE {clause}', (parameter,))
        row = cursor.fetchone()
        return _serialize(row) if row else None
    finally:
        cursor.close()
        conn.close()


def create_geofence(data: Dict, normalized_geometry: Dict) -> Dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    public_id = str(uuid4())
    try:
        conn.start_transaction()
        cursor.execute(
            """
            INSERT INTO monitoramento.geofences
                (public_id, nome, descricao, regra, status, owner_ref,
                 criado_por, atualizado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                public_id, data['nome'], data.get('descricao'), data['regra'],
                data['status'], data.get('owner_ref'), data['actor_id'], data['actor_id'],
            ),
        )
        geofence_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO monitoramento.geofence_versions
                (geofence_id, version_number, geometry_type, geometry,
                 radius_meters, geometry_hash, change_reason, created_by)
            VALUES (%s, 1, %s, ST_GeomFromText(%s), %s, %s, %s, %s)
            """,
            (
                geofence_id, normalized_geometry['type'], normalized_geometry['wkt'],
                normalized_geometry['radius_meters'], normalized_geometry['hash'],
                data['change_reason'], data['actor_id'],
            ),
        )
        cursor.execute(
            """
            INSERT INTO monitoramento.geofence_audit_log
                (geofence_id, action, from_version, to_version, actor, reason, details_json)
            VALUES (%s, 'created', NULL, 1, %s, %s, %s)
            """,
            (
                geofence_id, data['actor_id'], data['change_reason'],
                json.dumps({'geometry_type': normalized_geometry['type']}),
            ),
        )
        cursor.execute(GEOFENCE_SELECT + ' WHERE g.id = %s', (geofence_id,))
        result = _serialize(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def _locked_geofence(cursor, reference: str) -> Dict:
    if reference.isdigit():
        clause, parameter = 'id = %s', int(reference)
    else:
        clause, parameter = 'public_id = %s', reference
    cursor.execute(
        f'SELECT id, version, status FROM monitoramento.geofences WHERE {clause} FOR UPDATE',
        (parameter,),
    )
    row = cursor.fetchone()
    if row is None:
        raise GeofenceNotFound()
    return row


def _assert_mutable(row: Dict, expected_version: int) -> None:
    if row['status'] == 'archived':
        raise GeofenceArchived()
    if int(row['version']) != expected_version:
        raise GeofenceConflict()


def update_geofence(
    reference: str,
    data: Dict,
    normalized_geometry: Optional[Dict],
) -> Dict:
    """Atualiza metadados e cria versão geométrica somente quando o desenho mudou."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        row = _locked_geofence(cursor, reference)
        _assert_mutable(row, data['expected_version'])
        cursor.execute(
            """
            SELECT id, version_number, geometry_hash
              FROM monitoramento.geofence_versions
             WHERE geofence_id = %s
             ORDER BY version_number DESC LIMIT 1 FOR UPDATE
            """,
            (row['id'],),
        )
        current_geometry = cursor.fetchone()
        geometry_changed = bool(
            normalized_geometry
            and normalized_geometry['hash'] != current_geometry['geometry_hash']
        )
        next_version = int(row['version']) + 1
        cursor.execute(
            """
            UPDATE monitoramento.geofences
               SET nome = %s, descricao = %s, regra = %s, status = %s,
                   owner_ref = %s, atualizado_por = %s, version = %s
             WHERE id = %s AND version = %s
            """,
            (
                data['nome'], data.get('descricao'), data['regra'], data['status'],
                data.get('owner_ref'), data['actor_id'], next_version,
                row['id'], data['expected_version'],
            ),
        )
        if cursor.rowcount != 1:
            raise GeofenceConflict()

        if geometry_changed:
            cursor.execute(
                """
                UPDATE monitoramento.geofence_versions
                   SET valid_to = CURRENT_TIMESTAMP(6)
                 WHERE id = %s AND valid_to IS NULL
                """,
                (current_geometry['id'],),
            )
            cursor.execute(
                """
                INSERT INTO monitoramento.geofence_versions
                    (geofence_id, version_number, geometry_type, geometry,
                     radius_meters, geometry_hash, change_reason, created_by)
                VALUES (%s, %s, %s, ST_GeomFromText(%s), %s, %s, %s, %s)
                """,
                (
                    row['id'], int(current_geometry['version_number']) + 1,
                    normalized_geometry['type'], normalized_geometry['wkt'],
                    normalized_geometry['radius_meters'], normalized_geometry['hash'],
                    data['change_reason'], data['actor_id'],
                ),
            )

        action = 'geometry_updated' if geometry_changed else 'updated'
        cursor.execute(
            """
            INSERT INTO monitoramento.geofence_audit_log
                (geofence_id, action, from_version, to_version, actor, reason, details_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row['id'], action, row['version'], next_version, data['actor_id'],
                data['change_reason'], json.dumps({'geometry_changed': geometry_changed}),
            ),
        )
        cursor.execute(GEOFENCE_SELECT + ' WHERE g.id = %s', (row['id'],))
        result = _serialize(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def archive_geofence(reference: str, data: Dict) -> Dict:
    """Arquiva sem apagar histórico e bloqueia cercas ainda atribuídas."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        row = _locked_geofence(cursor, reference)
        _assert_mutable(row, data['expected_version'])
        cursor.execute(
            """
            SELECT COUNT(*) AS total
              FROM monitoramento.geofence_assignments
             WHERE geofence_id = %s AND ativo = TRUE
            """,
            (row['id'],),
        )
        active_assignments = int(cursor.fetchone()['total'])
        if active_assignments:
            raise GeofenceHasActiveAssignments(active_assignments)
        next_version = int(row['version']) + 1
        cursor.execute(
            """
            UPDATE monitoramento.geofences
               SET status = 'archived', atualizado_por = %s, version = %s
             WHERE id = %s AND version = %s
            """,
            (data['actor_id'], next_version, row['id'], data['expected_version']),
        )
        if cursor.rowcount != 1:
            raise GeofenceConflict()
        cursor.execute(
            """
            INSERT INTO monitoramento.geofence_audit_log
                (geofence_id, action, from_version, to_version, actor, reason, details_json)
            VALUES (%s, 'archived', %s, %s, %s, %s, NULL)
            """,
            (
                row['id'], row['version'], next_version,
                data['actor_id'], data['change_reason'],
            ),
        )
        cursor.execute(GEOFENCE_SELECT + ' WHERE g.id = %s', (row['id'],))
        result = _serialize(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
