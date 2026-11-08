#!/usr/bin/env python3
"""Copia alvos, análises e alertas reais para ``monitoramento``."""

import argparse
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.monitor_db import get_connection


ANALYSIS_COLUMNS = (
    'id', 'monitor_id', 'analisado_em', 'periodo_inicio', 'periodo_fim',
    'total_eventos', 'score_inicial', 'score_final', 'eventos_por_tipo',
    'conclusao', 'severidade',
)
ALERT_COLUMNS = (
    'id', 'analise_id', 'monitor_id', 'device_id', 'nome_motorista', 'titulo',
    'mensagem', 'severidade', 'tipo', 'criado_em', 'status', 'reconhecido_em',
    'reconhecido_por', 'total_eventos_relacionados',
)


def _upsert(cursor, table, columns, values):
    assignments = [
        f'{column} = VALUES({column})' for column in columns if column != 'id'
    ]
    cursor.execute(
        f'INSERT INTO monitoramento.{table} ({", ".join(columns)}) '
        f'VALUES ({", ".join(["%s"] * len(values))}) '
        f'ON DUPLICATE KEY UPDATE {", ".join(assignments)}',
        tuple(values),
    )


def resolve_target(cursor, assignment):
    if assignment['tipo_veiculo'] == 'tracker':
        if assignment.get('device_id'):
            cursor.execute("""
                SELECT vehicle_id
                  FROM monitoramento.veiculo_identidades
                 WHERE fonte_codigo = 'tracker'
                   AND tipo_identidade = 'device_id'
                   AND valor_externo = %s
                   AND ativo = TRUE
            """, (assignment['device_id'],))
        else:
            cursor.execute("""
                SELECT vehicle_id
                  FROM monitoramento.veiculo_identidades
                 WHERE fonte_codigo = 'tracker'
                   AND tipo_identidade = 'vehicle_id'
                   AND valor_externo = %s
                   AND ativo = TRUE
            """, (str(assignment.get('veicod_tracker') or ''),))
        rows = cursor.fetchall()
        if len(rows) != 1:
            raise RuntimeError(
                f'Alvo Tracker ambíguo para veiculomonitor {assignment["id"]}'
            )
        return 'vehicle', int(rows[0]['vehicle_id']), None, 'tracker'

    codusu = assignment.get('codusu_dirijabem')
    cursor.execute("""
        SELECT driver_id
          FROM monitoramento.motorista_identidades
         WHERE fonte_codigo = 'dirijabem'
           AND tipo_identidade = 'user_id'
           AND valor_externo = %s
           AND ativo = TRUE
    """, (str(codusu or ''),))
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise RuntimeError(
            f'Alvo Dirija Bem ambíguo para veiculomonitor {assignment["id"]}'
        )
    return 'driver', None, int(rows[0]['driver_id']), 'dirijabem'


def read_counts(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        counts = {}
        for schema, table in (
            ('tracker', 'veiculomonitor'),
            ('tracker', 'monitor_analises'),
            ('tracker', 'monitor_alertas'),
            ('monitoramento', 'monitor_targets'),
            ('monitoramento', 'monitor_analises'),
            ('monitoramento', 'monitor_alertas'),
        ):
            cursor.execute(f'SELECT COUNT(*) AS total FROM {schema}.{table}')
            counts[f'{schema}.{table}'] = int(cursor.fetchone()['total'])
        cursor.execute(
            'SELECT COUNT(*) AS total FROM tracker.monitor_alertas '
            'WHERE analise_id IS NULL'
        )
        counts['legacy_alerts_without_analysis'] = int(cursor.fetchone()['total'])
        return counts
    finally:
        cursor.close()


def apply_backfill(connection):
    source = connection.cursor(dictionary=True)
    target = connection.cursor(dictionary=True)
    try:
        source.execute('SELECT * FROM tracker.veiculomonitor ORDER BY id')
        for row in source.fetchall():
            target_type, vehicle_id, driver_id, source_code = resolve_target(target, row)
            columns = (
                'id', 'monitor_id', 'target_type', 'vehicle_id', 'driver_id',
                'fonte_codigo', 'legacy_veiculomonitor_id',
                'legacy_veicod_tracker', 'legacy_codusu_dirijabem',
                'legacy_device_id', 'ativo', 'atribuido_em',
            )
            values = (
                row['id'], row['monitor_id'], target_type, vehicle_id, driver_id,
                source_code, row['id'], row.get('veicod_tracker'),
                row.get('codusu_dirijabem'), row.get('device_id'), row['ativo'],
                row['atribuido_em'],
            )
            _upsert(target, 'monitor_targets', columns, values)

        source.execute('SELECT * FROM tracker.monitor_analises ORDER BY id')
        for row in source.fetchall():
            columns = (
                ANALYSIS_COLUMNS[:2]
                + ('monitor_target_id',)
                + ANALYSIS_COLUMNS[2:]
            )
            values = [row[column] for column in ANALYSIS_COLUMNS]
            values.insert(2, row['veiculomonitor_id'])
            _upsert(target, 'monitor_analises', columns, values)

        # Seeds antigos sem análise não entram na operação real. Continuam
        # preservados no legado para auditoria do processo de migração.
        source.execute("""
            SELECT a.*
              FROM tracker.monitor_alertas a
              JOIN tracker.monitor_analises ma ON ma.id = a.analise_id
             ORDER BY a.id
        """)
        for row in source.fetchall():
            columns = (
                ALERT_COLUMNS[:3]
                + ('monitor_target_id',)
                + ALERT_COLUMNS[3:]
            )
            values = [row[column] for column in ALERT_COLUMNS]
            values.insert(3, row['veiculomonitor_id'])
            _upsert(target, 'monitor_alertas', columns, values)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        source.close()
        target.close()


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
