"""API do estado patrimonial armado/desarmado."""

import logging
from flask import Blueprint, jsonify, request

from . import security_state_db


security_state_bp = Blueprint('security_state', __name__, url_prefix='/api/vehicles')
logger = logging.getLogger(__name__)


@security_state_bp.route('/<int:vehicle_id>/security-state', methods=['GET'])
def get_security_state(vehicle_id):
    try:
        result = security_state_db.get_state(vehicle_id, request.args.get('history_limit', 20))
        if result is None:
            return jsonify({'code': 'VEHICLE_NOT_FOUND'}), 404
        return jsonify(result)
    except Exception:
        logger.exception('Falha ao consultar estado patrimonial do veículo %s', vehicle_id)
        return jsonify({'code': 'SECURITY_STATE_UNAVAILABLE'}), 500


@security_state_bp.route('/<int:vehicle_id>/security-state/transitions', methods=['POST'])
def post_security_transition(vehicle_id):
    try:
        return jsonify(security_state_db.transition(vehicle_id, request.get_json(silent=True) or {}))
    except security_state_db.SecurityStateNotFound as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 404
    except security_state_db.SecurityStateConflict as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 409
    except security_state_db.SecurityStateError as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao alterar estado patrimonial do veículo %s', vehicle_id)
        return jsonify({'code': 'SECURITY_STATE_TRANSITION_FAILED'}), 500
