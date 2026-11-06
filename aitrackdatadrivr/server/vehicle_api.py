"""API versionada da identidade unificada de veículos."""

import logging
import os

from flask import Blueprint, jsonify

from . import monitor_db
from .unified_vehicle_dto import OperationMode, SCHEMA_VERSION, UnifiedVehicleDTO


vehicle_bp = Blueprint("vehicle_v1", __name__, url_prefix="/api/v1")
logger = logging.getLogger(__name__)


def _configured_mode(variable_name: str) -> OperationMode:
    raw_value = os.getenv(variable_name, OperationMode.UNKNOWN.value).strip().lower()
    try:
        return OperationMode(raw_value)
    except ValueError:
        logger.warning("Modo inválido em %s=%s; usando unknown", variable_name, raw_value)
        return OperationMode.UNKNOWN


@vehicle_bp.route("/vehicles", methods=["GET"])
def get_vehicles_v1():
    """Lista identidades no contrato ``vehicle.v1`` sem alterar APIs legadas."""
    try:
        tracker_mode = _configured_mode("AITRACK_TRACKER_MODE")
        dirijabem_mode = _configured_mode("AITRACK_DIRIJABEM_MODE")
        records = monitor_db.get_all_unified_vehicles()
        vehicles = [
            UnifiedVehicleDTO.from_record(
                record,
                tracker_mode=tracker_mode,
                dirijabem_mode=dirijabem_mode,
            ).to_dict()
            for record in records
        ]
        return jsonify({
            "schema_version": SCHEMA_VERSION,
            "total": len(vehicles),
            "vehicles": vehicles,
        })
    except Exception:
        logger.exception("Erro ao montar lista versionada de veículos")
        return jsonify({
            "error": "Não foi possível carregar as identidades dos veículos",
            "code": "UNIFIED_VEHICLES_UNAVAILABLE",
        }), 500
