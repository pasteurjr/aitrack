"""Leitura gradual da identidade operacional com fallback observável."""

import logging
import os
import re
from typing import Callable, Dict, List, Optional

from .monitor_db import get_connection


logger = logging.getLogger(__name__)
VALID_READ_MODES = {'legacy', 'shadow', 'operational'}


def configured_read_mode() -> str:
    mode = os.getenv('AITRACK_IDENTITY_READ_MODEL', 'shadow').strip().lower()
    if mode not in VALID_READ_MODES:
        logger.warning(
            'AITRACK_IDENTITY_READ_MODEL=%r inválido; usando shadow', mode,
        )
        return 'shadow'
    return mode


def legacy_vehicle_records() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT vu.id, vu.device_id, v.VEICOD AS veicod, vu.codusu,
                   vu.placa, vu.tipo, vu.descricao, vu.ativo
              FROM tracker.veiculo_unificado vu
         LEFT JOIN tracker.veiculos v ON v.VEI_DEVICE_ID = vu.device_id
             WHERE vu.ativo = TRUE
             ORDER BY vu.placa, vu.id
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def operational_vehicle_records() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT v.id,
                   (SELECT vi.valor_externo
                      FROM monitoramento.veiculo_identidades vi
                     WHERE vi.vehicle_id = v.id
                       AND vi.fonte_codigo = 'tracker'
                       AND vi.tipo_identidade = 'device_id'
                       AND vi.ativo = TRUE
                     ORDER BY vi.principal DESC, vi.id
                     LIMIT 1) AS device_id,
                   (SELECT CAST(vi.valor_externo AS UNSIGNED)
                      FROM monitoramento.veiculo_identidades vi
                     WHERE vi.vehicle_id = v.id
                       AND vi.fonte_codigo = 'tracker'
                       AND vi.tipo_identidade = 'vehicle_id'
                       AND vi.ativo = TRUE
                     ORDER BY vi.principal DESC, vi.id
                     LIMIT 1) AS veicod,
                   (SELECT CAST(mi.valor_externo AS UNSIGNED)
                      FROM monitoramento.veiculo_motorista_vinculos vmv
                      JOIN monitoramento.motorista_identidades mi
                        ON mi.driver_id = vmv.driver_id
                       AND mi.fonte_codigo = 'dirijabem'
                       AND mi.tipo_identidade = 'user_id'
                       AND mi.ativo = TRUE
                     WHERE vmv.vehicle_id = v.id
                     ORDER BY COALESCE(vmv.valido_ate, '9999-12-31') DESC,
                              vmv.valido_desde DESC, vmv.id DESC
                     LIMIT 1) AS codusu,
                   v.placa,
                   CASE
                     WHEN EXISTS (
                       SELECT 1 FROM monitoramento.veiculo_identidades vi
                        WHERE vi.vehicle_id = v.id
                          AND vi.fonte_codigo = 'tracker'
                          AND vi.ativo = TRUE
                     ) AND EXISTS (
                       SELECT 1 FROM monitoramento.veiculo_motorista_vinculos vmv
                        WHERE vmv.vehicle_id = v.id
                          AND vmv.fonte_codigo = 'dirijabem'
                     ) THEN 'both'
                     WHEN EXISTS (
                       SELECT 1 FROM monitoramento.veiculo_identidades vi
                        WHERE vi.vehicle_id = v.id
                          AND vi.fonte_codigo = 'tracker'
                          AND vi.ativo = TRUE
                     ) THEN 'tracker_only'
                     ELSE 'app_only'
                   END AS tipo,
                   v.descricao,
                   v.ativo
              FROM monitoramento.veiculos v
             WHERE v.ativo = TRUE AND v.merged_into_id IS NULL
             ORDER BY v.placa, v.id
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def _normalized_plates(records: List[Dict]) -> set:
    return {
        re.sub(r'[^A-Z0-9]', '', str(record['placa']).upper())
        for record in records
        if record.get('placa')
    }


def compare_read_models(legacy: List[Dict], operational: List[Dict]) -> Dict:
    legacy_plates = _normalized_plates(legacy)
    operational_plates = _normalized_plates(operational)
    return {
        'legacy_total': len(legacy),
        'operational_total': len(operational),
        'common_plates': len(legacy_plates & operational_plates),
        'only_legacy': len(legacy_plates - operational_plates),
        'only_operational': len(operational_plates - legacy_plates),
    }


def get_unified_vehicle_records(
    mode: Optional[str] = None,
    legacy_loader: Callable[[], List[Dict]] = legacy_vehicle_records,
    operational_loader: Callable[[], List[Dict]] = operational_vehicle_records,
) -> List[Dict]:
    """Seleciona o read model sem esconder falhas ou quebrar contratos legados."""
    mode = mode or configured_read_mode()
    if mode not in VALID_READ_MODES:
        raise ValueError(f'Modo de identidade inválido: {mode}')
    if mode == 'legacy':
        return legacy_loader()

    try:
        operational = operational_loader()
    except Exception:
        if mode == 'operational' and os.getenv(
            'AITRACK_IDENTITY_ALLOW_FALLBACK', '1',
        ).strip().lower() not in {'1', 'true', 'yes'}:
            raise
        logger.exception(
            'Read model operacional indisponível; usando identidade legada',
        )
        return legacy_loader()

    if mode == 'operational':
        return operational

    legacy = legacy_loader()
    comparison = compare_read_models(legacy, operational)
    logger.info('Comparação dos read models de identidade: %s', comparison)
    return legacy
