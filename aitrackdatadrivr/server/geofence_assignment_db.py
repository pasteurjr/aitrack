"""Alvos, grupos e vínculos operacionais das cercas eletrônicas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List
from uuid import uuid4

from .monitor_db import get_connection


class AssignmentNotFound(Exception):
    pass


class AssignmentConflict(Exception):
    pass


class InvalidAssignmentTarget(Exception):
    pass


def _serialize(row: Dict) -> Dict:
    result = {}
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif key in {'ativo', 'notify_on_entry', 'notify_on_exit', 'crosses_midnight'}:
            result[key] = bool(value)
        else:
            result[key] = value
    return result


def assignment_options() -> Dict[str, List[Dict]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, public_id, placa,
                   COALESCE(NULLIF(placa, ''), NULLIF(descricao, ''), public_id) AS label
              FROM monitoramento.veiculos
             WHERE ativo = TRUE AND merged_into_id IS NULL
             ORDER BY placa IS NULL, placa, descricao, id
        """)
        vehicles = cursor.fetchall()
        cursor.execute("""
            SELECT d.id, d.public_id,
                   COALESCE(NULLIF(d.nome, ''), CONCAT('Motorista #', d.id)) AS label,
                   (SELECT mi.valor_externo FROM monitoramento.motorista_identidades mi
                     WHERE mi.driver_id = d.id AND mi.fonte_codigo = 'dirijabem'
                       AND mi.tipo_identidade = 'user_id' AND mi.ativo = TRUE
                     LIMIT 1) AS codusu
              FROM monitoramento.motoristas d
             WHERE d.ativo = TRUE
             ORDER BY d.nome IS NULL, d.nome, d.id
        """)
        drivers = cursor.fetchall()
        cursor.execute("""
            SELECT g.id, g.public_id, g.nome AS label,
                   (SELECT COUNT(*) FROM monitoramento.monitoring_group_members gm
                     WHERE gm.group_id = g.id AND gm.ativo = TRUE) AS member_count
              FROM monitoramento.monitoring_groups g
             WHERE g.ativo = TRUE
             ORDER BY g.nome, g.id
        """)
        groups = cursor.fetchall()
        return {
            'vehicles': [_serialize(row) for row in vehicles],
            'drivers': [_serialize(row) for row in drivers],
            'groups': [_serialize(row) for row in groups],
        }
    finally:
        cursor.close()
        conn.close()


def create_group(data: Dict) -> Dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    public_id = str(uuid4())
    try:
        conn.start_transaction()
        cursor.execute("""
            INSERT INTO monitoramento.monitoring_groups
                (public_id, nome, descricao, owner_ref, criado_por, atualizado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            public_id, data['nome'], data.get('descricao'), data.get('owner_ref'),
            data['actor_id'], data['actor_id'],
        ))
        group_id = cursor.lastrowid
        for vehicle_id in data['vehicle_ids']:
            cursor.execute("""
                INSERT INTO monitoramento.monitoring_group_members
                    (group_id, member_type, vehicle_id, adicionado_por)
                SELECT %s, 'vehicle', id, %s FROM monitoramento.veiculos
                 WHERE id = %s AND ativo = TRUE AND merged_into_id IS NULL
            """, (group_id, data['actor_id'], vehicle_id))
            if cursor.rowcount != 1:
                raise InvalidAssignmentTarget()
        for driver_id in data['driver_ids']:
            cursor.execute("""
                INSERT INTO monitoramento.monitoring_group_members
                    (group_id, member_type, driver_id, adicionado_por)
                SELECT %s, 'driver', id, %s FROM monitoramento.motoristas
                 WHERE id = %s AND ativo = TRUE
            """, (group_id, data['actor_id'], driver_id))
            if cursor.rowcount != 1:
                raise InvalidAssignmentTarget()
        cursor.execute("""
            SELECT g.id, g.public_id, g.nome AS label,
                   COUNT(gm.id) AS member_count
              FROM monitoramento.monitoring_groups g
         LEFT JOIN monitoramento.monitoring_group_members gm
                ON gm.group_id = g.id AND gm.ativo = TRUE
             WHERE g.id = %s GROUP BY g.id
        """, (group_id,))
        result = _serialize(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


ASSIGNMENT_SELECT = """
    SELECT ga.id, ga.geofence_id, ga.target_type, ga.vehicle_id, ga.driver_id,
           ga.group_id, ga.timezone_name, ga.effective_from, ga.effective_to,
           ga.notify_on_entry, ga.notify_on_exit, ga.dwell_threshold_seconds,
           ga.hysteresis_meters, ga.cooldown_seconds, ga.priority, ga.ativo,
           ga.version, ga.criado_por, ga.atualizado_por, ga.criado_em, ga.atualizado_em,
           CASE ga.target_type
             WHEN 'vehicle' THEN COALESCE(v.placa, v.descricao, CONCAT('Veículo #', v.id))
             WHEN 'driver' THEN COALESCE(d.nome, CONCAT('Motorista #', d.id))
             WHEN 'group' THEN g.nome
           END AS target_label
      FROM monitoramento.geofence_assignments ga
 LEFT JOIN monitoramento.veiculos v ON v.id = ga.vehicle_id
 LEFT JOIN monitoramento.motoristas d ON d.id = ga.driver_id
 LEFT JOIN monitoramento.monitoring_groups g ON g.id = ga.group_id
"""


def _geofence(cursor, reference: str) -> Dict:
    column = 'id' if reference.isdigit() else 'public_id'
    cursor.execute(
        f'SELECT id, regra, status FROM monitoramento.geofences WHERE {column} = %s',
        (int(reference) if reference.isdigit() else reference,),
    )
    row = cursor.fetchone()
    if not row or row['status'] == 'archived':
        raise AssignmentNotFound()
    return row


def list_assignments(reference: str, include_inactive: bool = False) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        fence = _geofence(cursor, reference)
        active_clause = '' if include_inactive else ' AND ga.ativo = TRUE'
        cursor.execute(
            ASSIGNMENT_SELECT + f' WHERE ga.geofence_id = %s{active_clause} ORDER BY ga.ativo DESC, ga.id',
            (fence['id'],),
        )
        assignments = [_serialize(row) for row in cursor.fetchall()]
        for assignment in assignments:
            cursor.execute("""
                SELECT id, day_of_week, CAST(start_time AS CHAR) AS start_time,
                       CAST(end_time AS CHAR) AS end_time,
                       crosses_midnight, ativo
                  FROM monitoramento.geofence_assignment_schedules
                 WHERE assignment_id = %s AND ativo = TRUE
                 ORDER BY day_of_week, start_time, id
            """, (assignment['id'],))
            assignment['schedules'] = [_serialize(row) for row in cursor.fetchall()]
        return assignments
    finally:
        cursor.close()
        conn.close()


def assign_target(reference: str, data: Dict) -> Dict:
    target_column = {'vehicle': 'vehicle_id', 'driver': 'driver_id', 'group': 'group_id'}[
        data['target_type']
    ]
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        fence = _geofence(cursor, reference)
        target_table = {
            'vehicle': ('monitoramento.veiculos', 'ativo = TRUE AND merged_into_id IS NULL'),
            'driver': ('monitoramento.motoristas', 'ativo = TRUE'),
            'group': ('monitoramento.monitoring_groups', 'ativo = TRUE'),
        }[data['target_type']]
        cursor.execute(
            f'SELECT id FROM {target_table[0]} WHERE id = %s AND {target_table[1]}',
            (data['target_id'],),
        )
        if cursor.fetchone() is None:
            raise InvalidAssignmentTarget()
        cursor.execute(
            f'SELECT id, version, ativo FROM monitoramento.geofence_assignments '
            f'WHERE geofence_id = %s AND {target_column} = %s FOR UPDATE',
            (fence['id'], data['target_id']),
        )
        existing = cursor.fetchone()
        notify_entry = data.get('notify_on_entry', fence['regra'] == 'forbidden')
        notify_exit = data.get('notify_on_exit', fence['regra'] == 'allowed')
        if existing:
            if existing['ativo']:
                raise AssignmentConflict()
            cursor.execute("""
                UPDATE monitoramento.geofence_assignments
                   SET ativo = TRUE, notify_on_entry = %s, notify_on_exit = %s,
                       atualizado_por = %s, version = version + 1
                 WHERE id = %s AND version = %s
            """, (notify_entry, notify_exit, data['actor_id'], existing['id'], existing['version']))
            assignment_id = existing['id']
        else:
            references = {'vehicle_id': None, 'driver_id': None, 'group_id': None}
            references[target_column] = data['target_id']
            cursor.execute("""
                INSERT INTO monitoramento.geofence_assignments
                    (geofence_id, target_type, vehicle_id, driver_id, group_id,
                     notify_on_entry, notify_on_exit, criado_por, atualizado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                fence['id'], data['target_type'], references['vehicle_id'],
                references['driver_id'], references['group_id'], notify_entry,
                notify_exit, data['actor_id'], data['actor_id'],
            ))
            assignment_id = cursor.lastrowid
        cursor.execute(ASSIGNMENT_SELECT + ' WHERE ga.id = %s', (assignment_id,))
        result = _serialize(cursor.fetchone())
        result['schedules'] = []
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def deactivate_assignment(reference: str, assignment_id: int, data: Dict) -> Dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        fence = _geofence(cursor, reference)
        cursor.execute("""
            SELECT id, version, ativo FROM monitoramento.geofence_assignments
             WHERE id = %s AND geofence_id = %s FOR UPDATE
        """, (assignment_id, fence['id']))
        row = cursor.fetchone()
        if not row:
            raise AssignmentNotFound()
        if int(row['version']) != data['expected_version']:
            raise AssignmentConflict()
        cursor.execute("""
            UPDATE monitoramento.geofence_assignments
               SET ativo = FALSE, atualizado_por = %s, version = version + 1
             WHERE id = %s AND version = %s
        """, (data['actor_id'], assignment_id, data['expected_version']))
        cursor.execute(ASSIGNMENT_SELECT + ' WHERE ga.id = %s', (assignment_id,))
        result = _serialize(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def update_assignment_policy(reference: str, assignment_id: int, data: Dict) -> Dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        fence = _geofence(cursor, reference)
        cursor.execute("""
            SELECT id, version FROM monitoramento.geofence_assignments
             WHERE id = %s AND geofence_id = %s AND ativo = TRUE FOR UPDATE
        """, (assignment_id, fence['id']))
        row = cursor.fetchone()
        if not row:
            raise AssignmentNotFound()
        if int(row['version']) != data['expected_version']:
            raise AssignmentConflict()
        cursor.execute("""
            UPDATE monitoramento.geofence_assignments
               SET timezone_name = %s, dwell_threshold_seconds = %s,
                   atualizado_por = %s, version = version + 1
             WHERE id = %s AND version = %s
        """, (
            data['timezone_name'], data['dwell_threshold_seconds'], data['actor_id'],
            assignment_id, data['expected_version'],
        ))
        cursor.execute("""
            UPDATE monitoramento.geofence_assignment_schedules
               SET ativo = FALSE WHERE assignment_id = %s AND ativo = TRUE
        """, (assignment_id,))
        for schedule in data['schedules']:
            cursor.execute("""
                INSERT INTO monitoramento.geofence_assignment_schedules
                    (assignment_id, day_of_week, start_time, end_time,
                     crosses_midnight, ativo)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE ativo = TRUE
            """, (
                assignment_id, schedule['day_of_week'], schedule['start_time'],
                schedule['end_time'], schedule['crosses_midnight'],
            ))
        cursor.execute(ASSIGNMENT_SELECT + ' WHERE ga.id = %s', (assignment_id,))
        result = _serialize(cursor.fetchone())
        cursor.execute("""
            SELECT id, day_of_week, CAST(start_time AS CHAR) AS start_time,
                   CAST(end_time AS CHAR) AS end_time,
                   crosses_midnight, ativo
              FROM monitoramento.geofence_assignment_schedules
             WHERE assignment_id = %s AND ativo = TRUE
             ORDER BY day_of_week, start_time, id
        """, (assignment_id,))
        result['schedules'] = [_serialize(item) for item in cursor.fetchall()]
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
