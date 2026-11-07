#!/usr/bin/env python3
"""Copia monitores, incidentes e timeline sem modificar tabelas legadas."""

import argparse
from pathlib import Path
import re
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.monitor_db import get_connection


INCIDENT_COLUMNS = (
    'id', 'correlation_key', 'monitor_id', 'origin_episode_id', 'incident_type',
    'title', 'summary', 'status', 'severity', 'risk_score', 'primary_source',
    'driver_ref', 'owner_ref', 'assigned_type', 'assigned_to', 'latitude',
    'longitude', 'position_observed_at', 'hypothesis', 'confidence',
    'context_snapshot', 'opened_at', 'triaged_at', 'acknowledged_at',
    'sla_due_at', 'next_action_at', 'resolved_at', 'closed_at',
    'resolution_code', 'resolution_notes', 'false_positive',
    'detection_outcome', 'classification_reason', 'classified_by',
    'classified_at', 'event_count', 'version', 'created_at', 'updated_at',
)
TIMELINE_COLUMNS = (
    'id', 'incident_id', 'idempotency_key', 'entry_type', 'actor_type',
    'actor_id', 'actor_name', 'from_status', 'to_status', 'summary', 'details',
    'event_id', 'evidence_type', 'evidence_ref', 'correlation_id',
    'causation_id', 'visibility', 'occurred_at', 'recorded_at',
)


def normalize_plate(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper()) or None


def _upsert(cursor, table, columns, values, extra_updates=()):
    assignments = [
        f'{column} = VALUES({column})' for column in columns if column != 'id'
    ]
    assignments.extend(extra_updates)
    placeholders = ', '.join(['%s'] * len(values))
    cursor.execute(
        f'INSERT INTO monitoramento.{table} ({", ".join(columns)}) '
        f'VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {", ".join(assignments)}',
        tuple(values),
    )


def resolve_canonical_vehicle(cursor, legacy_vehicle_id):
    cursor.execute("""
        SELECT device_id, placa
          FROM tracker.veiculo_unificado
         WHERE id = %s AND ativo = TRUE
    """, (legacy_vehicle_id,))
    legacy = cursor.fetchone()
    if not legacy:
        raise RuntimeError(f'Veículo legado ativo não encontrado: {legacy_vehicle_id}')

    if legacy.get('device_id'):
        cursor.execute("""
            SELECT vehicle_id
              FROM monitoramento.veiculo_identidades
             WHERE fonte_codigo = 'tracker'
               AND tipo_identidade = 'device_id'
               AND valor_externo = %s
               AND ativo = TRUE
        """, (legacy['device_id'],))
    else:
        plate = normalize_plate(legacy.get('placa'))
        cursor.execute(
            'SELECT id AS vehicle_id FROM monitoramento.veiculos '
            'WHERE placa = %s AND ativo = TRUE AND merged_into_id IS NULL',
            (plate,),
        )
    matches = cursor.fetchall()
    if len(matches) != 1:
        raise RuntimeError(
            f'Mapeamento canônico inválido para veículo legado {legacy_vehicle_id}: '
            f'{len(matches)} correspondências'
        )
    return int(matches[0]['vehicle_id'])


def read_counts(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        counts = {}
        for schema, table in (
            ('tracker', 'monitores'),
            ('tracker', 'incidents'),
            ('tracker', 'incident_timeline'),
            ('monitoramento', 'monitores'),
            ('monitoramento', 'incidents'),
            ('monitoramento', 'incident_timeline'),
        ):
            cursor.execute(f'SELECT COUNT(*) AS total FROM {schema}.{table}')
            counts[f'{schema}.{table}'] = int(cursor.fetchone()['total'])
        return counts
    finally:
        cursor.close()


def apply_backfill(connection):
    read_cursor = connection.cursor(dictionary=True)
    write_cursor = connection.cursor(dictionary=True)
    try:
        read_cursor.execute('SELECT * FROM tracker.monitores ORDER BY id')
        for row in read_cursor.fetchall():
            columns = tuple(row.keys())
            _upsert(write_cursor, 'monitores', columns, [row[col] for col in columns])

        read_cursor.execute('SELECT * FROM tracker.incidents ORDER BY id')
        incidents = read_cursor.fetchall()
        for row in incidents:
            canonical_vehicle_id = resolve_canonical_vehicle(
                write_cursor, int(row['vehicle_id']),
            )
            values = [row[column] for column in INCIDENT_COLUMNS]
            columns = (
                INCIDENT_COLUMNS[:2]
                + ('vehicle_id', 'legacy_vehicle_id')
                + INCIDENT_COLUMNS[2:]
            )
            values = values[:2] + [
                canonical_vehicle_id, row['vehicle_id'],
            ] + values[2:]
            _upsert(write_cursor, 'incidents', columns, values)

        read_cursor.execute('SELECT * FROM tracker.incident_timeline ORDER BY id')
        for row in read_cursor.fetchall():
            values = [row[column] for column in TIMELINE_COLUMNS]
            event_source = 'tracker' if row.get('event_id') is not None else None
            event_index = TIMELINE_COLUMNS.index('event_id') + 1
            columns = (
                TIMELINE_COLUMNS[:event_index]
                + ('event_source',)
                + TIMELINE_COLUMNS[event_index:]
            )
            values.insert(event_index, event_source)
            _upsert(write_cursor, 'incident_timeline', columns, values)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        read_cursor.close()
        write_cursor.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='confirma a escrita')
    args = parser.parse_args(argv)
    connection = get_connection()
    try:
        before = read_counts(connection)
        print('antes ' + ' '.join(f'{key}={value}' for key, value in before.items()))
        if not args.apply:
            print('dry-run: nenhuma escrita realizada; use --apply para confirmar')
            return 0
        apply_backfill(connection)
        after = read_counts(connection)
        print('depois ' + ' '.join(f'{key}={value}' for key, value in after.items()))
        return 0
    finally:
        connection.close()


if __name__ == '__main__':
    raise SystemExit(main())
