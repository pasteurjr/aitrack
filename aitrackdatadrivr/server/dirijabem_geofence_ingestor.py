"""Cauda incremental das posições externas do Dirija Bem para o motor de cercas."""

import logging
import os
import time
from datetime import datetime

from .geofence_engine import evaluate_dirijabem_position
from .monitor_db import get_connection


LOGGER = logging.getLogger(__name__)
SOURCE = 'dirijabem'
STREAM = 'localizacaodados_geofences'
POLL_SECONDS = max(0.2, float(os.getenv('DIRIJABEM_GEOFENCE_POLL_SECONDS', '1')))
BATCH_SIZE = max(1, min(1000, int(os.getenv('DIRIJABEM_GEOFENCE_BATCH_SIZE', '200'))))
REWIND_IDS = max(BATCH_SIZE, int(os.getenv('DIRIJABEM_GEOFENCE_REWIND_IDS', '10000')))
MAX_FAILURE_ATTEMPTS = max(1, int(os.getenv('DIRIJABEM_GEOFENCE_MAX_FAILURES', '3')))


def rewind_start(offset: int, window: int = REWIND_IDS) -> int:
    """Watermark conservador para capturar commits fora da ordem do AUTO_INCREMENT."""
    return max(0, int(offset) - max(1, int(window)))


def _load_or_initialize_offset(cursor) -> int:
    cursor.execute("""
        SELECT last_external_id
          FROM monitoramento.source_ingestion_offsets
         WHERE source_code = %s AND stream_name = %s
    """, (SOURCE, STREAM))
    row = cursor.fetchone()
    if row:
        return int(row['last_external_id'])
    # Primeira ativação acompanha somente posições novas para não varrer a tabela
    # histórica (dezenas de milhões de linhas) nem criar alertas retroativos.
    cursor.execute(
        'SELECT COALESCE(MAX(LOCDADCOD), 0) AS offset '
        'FROM dirijabem.localizacaodados',
    )
    offset = int(cursor.fetchone()['offset'])
    cursor.execute("""
        INSERT INTO monitoramento.source_ingestion_offsets
            (source_code, stream_name, last_external_id)
        VALUES (%s, %s, %s)
    """, (SOURCE, STREAM, offset))
    return offset


def poll_once() -> int:
    """Processa um lote em ordem de PK e retorna a quantidade consumida."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        offset = _load_or_initialize_offset(cursor)
        conn.commit()
        start_id = rewind_start(offset)
        cursor.execute("""
            SELECT l.LOCDADCOD AS position_id, l.DATAHORA AS observed_at,
                   ST_X(l.coords) AS longitude, ST_Y(l.coords) AS latitude,
                   v.CODUSU AS user_id, v.PLACA AS plate
              FROM dirijabem.localizacaodados l
              JOIN dirijabem.viagem v ON v.CODVIA = l.CODVIA
         LEFT JOIN monitoramento.source_position_receipts r
                ON r.source_code = %s
               AND r.external_position_id =
                   (CAST(l.LOCDADCOD AS CHAR) COLLATE utf8mb4_unicode_ci)
             WHERE l.LOCDADCOD > %s AND l.coords IS NOT NULL
               AND r.external_position_id IS NULL
             ORDER BY l.LOCDADCOD
             LIMIT %s
        """, (SOURCE, start_id, BATCH_SIZE))
        rows = cursor.fetchall()
        conn.commit()
        last_processed = offset
        for row in rows:
            received_at = datetime.now()
            try:
                evaluate_dirijabem_position(
                    user_id=row['user_id'],
                    longitude=row['longitude'],
                    latitude=row['latitude'],
                    observed_at=row['observed_at'],
                    plate=row['plate'],
                    received_at=received_at,
                    external_position_id=row['position_id'],
                )
                cursor.execute("""
                    INSERT INTO monitoramento.source_position_receipts
                        (source_code, external_position_id, received_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE external_position_id = external_position_id
                """, (SOURCE, str(row['position_id']), received_at))
                cursor.execute("""
                    DELETE FROM monitoramento.source_ingestion_failures
                     WHERE source_code = %s AND stream_name = %s
                       AND external_position_id = %s
                """, (SOURCE, STREAM, str(row['position_id'])))
            except Exception as error:
                LOGGER.exception('Posição Dirija Bem %s falhou', row['position_id'])
                cursor.execute("""
                    INSERT INTO monitoramento.source_ingestion_failures
                        (source_code, stream_name, external_position_id, last_error)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        attempts = attempts + 1,
                        last_error = VALUES(last_error),
                        last_failed_at = CURRENT_TIMESTAMP(6)
                """, (SOURCE, STREAM, str(row['position_id']), str(error)[:1000]))
                cursor.execute("""
                    SELECT attempts FROM monitoramento.source_ingestion_failures
                     WHERE source_code = %s AND stream_name = %s
                       AND external_position_id = %s
                """, (SOURCE, STREAM, str(row['position_id'])))
                if int(cursor.fetchone()['attempts']) >= MAX_FAILURE_ATTEMPTS:
                    cursor.execute("""
                        UPDATE monitoramento.source_ingestion_failures
                           SET status = 'quarantined'
                         WHERE source_code = %s AND stream_name = %s
                           AND external_position_id = %s
                    """, (SOURCE, STREAM, str(row['position_id'])))
                    cursor.execute("""
                        INSERT INTO monitoramento.source_position_receipts
                            (source_code, external_position_id, received_at)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE external_position_id = external_position_id
                    """, (SOURCE, str(row['position_id']), received_at))
            last_processed = max(last_processed, int(row['position_id']))
        if last_processed != offset:
            cursor.execute("""
                UPDATE monitoramento.source_ingestion_offsets
                   SET last_external_id = %s
                 WHERE source_code = %s AND stream_name = %s
                   AND last_external_id <= %s
            """, (last_processed, SOURCE, STREAM, last_processed))
        cursor.execute("""
            DELETE FROM monitoramento.source_position_receipts
             WHERE source_code = %s
               AND external_position_id REGEXP '^[0-9]+$'
               AND CAST(external_position_id AS UNSIGNED) <= %s
        """, (SOURCE, rewind_start(last_processed)))
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def run_forever() -> None:
    LOGGER.info('Ingestor de cercas Dirija Bem iniciado')
    while True:
        try:
            processed = poll_once()
            if processed >= BATCH_SIZE:
                continue
        except Exception:
            LOGGER.exception('Falha no consumo de posições Dirija Bem; nova tentativa agendada')
        time.sleep(POLL_SECONDS)
