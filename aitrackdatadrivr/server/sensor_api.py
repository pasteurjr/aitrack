"""API de sensores observados por veículo operacional."""

import logging

from flask import Blueprint, jsonify

from . import sensor_db


sensor_bp = Blueprint('sensors', __name__, url_prefix='/api/vehicles')
logger = logging.getLogger(__name__)


@sensor_bp.route('/<int:vehicle_id>/sensors', methods=['GET'])
def get_vehicle_sensors(vehicle_id):
    try:
        result = sensor_db.get_vehicle_sensors(vehicle_id)
        if result is None:
            return jsonify({
                'code': 'VEHICLE_NOT_FOUND',
                'error': 'Veículo operacional não encontrado',
            }), 404
        return jsonify(result)
    except Exception:
        logger.exception('Falha ao consultar sensores do veículo %s', vehicle_id)
        return jsonify({
            'code': 'VEHICLE_SENSORS_UNAVAILABLE',
            'error': 'Sensores temporariamente indisponíveis',
        }), 500
