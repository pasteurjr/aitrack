#!/usr/bin/env python3
"""Copia identidades legadas para ``monitoramento`` sem alterar as fontes."""

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
import uuid

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.monitor_db import get_connection


IDENTITY_NAMESPACE = uuid.UUID('a6ca21a3-82cd-45e0-bbc9-9cb2252de6ec')


def normalize_plate(value):
    normalized = re.sub(r'[^A-Z0-9]', '', str(value or '').upper())
    return normalized or None


def stable_public_id(entity, source_key):
    return str(uuid.uuid5(IDENTITY_NAMESPACE, f'{entity}:{source_key}'))


def _placeholders(values):
    return ','.join(['%s'] * len(values))


def read_source_snapshot(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT vu.id, vu.device_id, vu.codusu, vu.placa, vu.descricao,
                   vu.tipo, vu.ativo, v.VEICOD AS tracker_vehicle_id
              FROM tracker.veiculo_unificado vu
         LEFT JOIN tracker.veiculos v ON v.VEI_DEVICE_ID = vu.device_id
             ORDER BY vu.id
             LIMIT 1000
        """)
        legacy = cursor.fetchall()
        codusus = sorted({int(row['codusu']) for row in legacy if row['codusu'] is not None})
        trips = []
        if codusus:
            cursor.execute(f"""
                SELECT CODUSU, UPPER(TRIM(PLACA)) AS placa,
                       MIN(DATAHORINI) AS valido_desde,
                       MAX(COALESCE(DATAHORFIN, DATAHORINI)) AS valido_ate,
                       COUNT(*) AS viagens
                  FROM dirijabem.viagem
                 WHERE CODUSU IN ({_placeholders(codusus)})
                   AND PLACA IS NOT NULL
                   AND TRIM(PLACA) <> ''
              GROUP BY CODUSU, UPPER(TRIM(PLACA))
              ORDER BY CODUSU, UPPER(TRIM(PLACA))
            """, tuple(codusus))
            trips = cursor.fetchall()
        return legacy, trips
    finally:
        cursor.close()


def expected_counts(legacy, trips):
    tracker_rows = [row for row in legacy if row.get('device_id')]
    drivers = {int(row['codusu']) for row in legacy if row.get('codusu') is not None}
    vehicle_keys = set()
    for row in tracker_rows:
        plate = normalize_plate(row.get('placa'))
        vehicle_keys.add(f'plate:{plate}' if plate else f'device:{row["device_id"]}')
    for trip in trips:
        plate = normalize_plate(trip.get('placa'))
        if plate:
            vehicle_keys.add(f'plate:{plate}')
    return {
        'vehicles': len(vehicle_keys),
        'drivers': len(drivers),
        'tracker_rows': len(tracker_rows),
        'driver_vehicle_links': len(trips),
    }


def _get_or_create_vehicle(cursor, source_key, plate, description):
    public_id = stable_public_id('vehicle', source_key)
    cursor.execute("""
        INSERT INTO monitoramento.veiculos
            (public_id, placa, descricao, ativo)
        VALUES (%s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE
            placa = COALESCE(placa, VALUES(placa)),
            descricao = COALESCE(descricao, VALUES(descricao)),
            ativo = TRUE
    """, (public_id, plate, description))
    cursor.execute(
        'SELECT id FROM monitoramento.veiculos WHERE public_id = %s',
        (public_id,),
    )
    return int(cursor.fetchone()['id'])


def _get_or_create_driver(cursor, codusu):
    public_id = stable_public_id('driver', f'dirijabem-user:{codusu}')
    cursor.execute("""
        INSERT INTO monitoramento.motoristas (public_id, ativo)
        VALUES (%s, TRUE)
        ON DUPLICATE KEY UPDATE ativo = TRUE
    """, (public_id,))
    cursor.execute(
        'SELECT id FROM monitoramento.motoristas WHERE public_id = %s',
        (public_id,),
    )
    return int(cursor.fetchone()['id'])


def _ensure_vehicle_identity(cursor, vehicle_id, source, identity_type, value, primary=False):
    value = str(value).strip()
    cursor.execute("""
        SELECT vehicle_id
          FROM monitoramento.veiculo_identidades
         WHERE fonte_codigo = %s AND tipo_identidade = %s AND valor_externo = %s
         FOR UPDATE
    """, (source, identity_type, value))
    existing = cursor.fetchone()
    if existing and int(existing['vehicle_id']) != vehicle_id:
        raise RuntimeError(
            f'Identidade conflitante: {source}/{identity_type}/{value}'
        )
    if not existing:
        cursor.execute("""
            INSERT INTO monitoramento.veiculo_identidades
                (vehicle_id, fonte_codigo, tipo_identidade, valor_externo,
                 principal, ativo, primeiro_visto_em, ultimo_visto_em)
            VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP(6),
                    CURRENT_TIMESTAMP(6))
        """, (vehicle_id, source, identity_type, value, primary))


def _ensure_driver_identity(cursor, driver_id, codusu):
    value = str(codusu)
    cursor.execute("""
        SELECT driver_id
          FROM monitoramento.motorista_identidades
         WHERE fonte_codigo = 'dirijabem'
           AND tipo_identidade = 'user_id'
           AND valor_externo = %s
         FOR UPDATE
    """, (value,))
    existing = cursor.fetchone()
    if existing and int(existing['driver_id']) != driver_id:
        raise RuntimeError(f'Identidade de motorista conflitante: dirijabem/{value}')
    if not existing:
        cursor.execute("""
            INSERT INTO monitoramento.motorista_identidades
                (driver_id, fonte_codigo, tipo_identidade, valor_externo, ativo)
            VALUES (%s, 'dirijabem', 'user_id', %s, TRUE)
        """, (driver_id, value))


def apply_backfill(connection, legacy, trips):
    cursor = connection.cursor(dictionary=True)
    drivers = {}
    try:
        for row in legacy:
            device_id = str(row.get('device_id') or '').strip()
            if device_id:
                plate = normalize_plate(row.get('placa'))
                source_key = f'plate:{plate}' if plate else f'device:{device_id}'
                vehicle_id = _get_or_create_vehicle(
                    cursor, source_key, plate, row.get('descricao'),
                )
                _ensure_vehicle_identity(
                    cursor, vehicle_id, 'tracker', 'device_id', device_id, True,
                )
                if row.get('tracker_vehicle_id') is not None:
                    _ensure_vehicle_identity(
                        cursor, vehicle_id, 'tracker', 'vehicle_id',
                        row['tracker_vehicle_id'], False,
                    )
                if plate:
                    _ensure_vehicle_identity(
                        cursor, vehicle_id, 'tracker', 'plate', plate, False,
                    )
            if row.get('codusu') is not None:
                codusu = int(row['codusu'])
                driver_id = drivers.get(codusu)
                if driver_id is None:
                    driver_id = _get_or_create_driver(cursor, codusu)
                    drivers[codusu] = driver_id
                _ensure_driver_identity(cursor, driver_id, codusu)

        for trip in trips:
            codusu = int(trip['CODUSU'])
            plate = normalize_plate(trip['placa'])
            if not plate:
                continue
            driver_id = drivers.get(codusu) or _get_or_create_driver(cursor, codusu)
            drivers[codusu] = driver_id
            _ensure_driver_identity(cursor, driver_id, codusu)
            vehicle_id = _get_or_create_vehicle(
                cursor, f'plate:{plate}', plate, f'Veículo Dirija Bem {plate}',
            )
            _ensure_vehicle_identity(
                cursor, vehicle_id, 'dirijabem', 'plate', plate, True,
            )
            valid_from = trip['valido_desde'] or datetime(1970, 1, 1)
            valid_to = trip['valido_ate'] or valid_from
            cursor.execute("""
                INSERT INTO monitoramento.veiculo_motorista_vinculos
                    (vehicle_id, driver_id, fonte_codigo, valido_desde, valido_ate)
                VALUES (%s, %s, 'dirijabem', %s, %s)
                ON DUPLICATE KEY UPDATE
                    valido_ate = GREATEST(valido_ate, VALUES(valido_ate))
            """, (vehicle_id, driver_id, valid_from, valid_to))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def operational_counts(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        counts = {}
        for name in (
            'veiculos', 'veiculo_identidades', 'motoristas',
            'motorista_identidades', 'veiculo_motorista_vinculos',
        ):
            cursor.execute(f'SELECT COUNT(*) AS total FROM monitoramento.{name}')
            counts[name] = int(cursor.fetchone()['total'])
        return counts
    finally:
        cursor.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='confirma a escrita')
    args = parser.parse_args(argv)
    connection = get_connection()
    try:
        legacy, trips = read_source_snapshot(connection)
        expected = expected_counts(legacy, trips)
        print('plano ' + ' '.join(f'{key}={value}' for key, value in expected.items()))
        if not args.apply:
            print('dry-run: nenhuma escrita realizada; use --apply para confirmar')
            return 0
        apply_backfill(connection, legacy, trips)
        counts = operational_counts(connection)
        print('resultado ' + ' '.join(f'{key}={value}' for key, value in counts.items()))
        return 0
    finally:
        connection.close()


if __name__ == '__main__':
    raise SystemExit(main())
