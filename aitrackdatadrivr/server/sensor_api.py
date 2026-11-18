"""API de sensores observados por veículo operacional."""

import logging

from flask import Blueprint, jsonify, request

from . import sensor_db
from . import power_detector


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


@sensor_bp.route('/<int:vehicle_id>/detector-episodes', methods=['GET'])
def get_detector_episodes(vehicle_id):
    try:
        return jsonify(power_detector.list_episodes(
            vehicle_id, request.args.get('status'), request.args.get('limit', 50),
        ))
    except ValueError as exc:
        return jsonify({'code': 'INVALID_DETECTOR_EPISODE_FILTER', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao consultar episódios do veículo %s', vehicle_id)
        return jsonify({'code': 'DETECTOR_EPISODES_UNAVAILABLE'}), 500
