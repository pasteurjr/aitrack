"""API de políticas versionadas dos detectores."""

import logging

from flask import Blueprint, jsonify, request

from . import detector_policy_db


detector_policy_bp = Blueprint(
    'detector_policies', __name__, url_prefix='/api/detector-policies',
)
logger = logging.getLogger(__name__)


@detector_policy_bp.route('', methods=['GET'])
def get_policies():
    try:
        policies = detector_policy_db.list_policies(request.args.get('status'))
        return jsonify({
            'schema_version': 'detector-policies.v1',
            'count': len(policies),
            'policies': policies,
        })
    except Exception:
        logger.exception('Falha ao listar políticas de detector')
        return jsonify({'code': 'DETECTOR_POLICIES_UNAVAILABLE'}), 500


@detector_policy_bp.route('', methods=['POST'])
def post_policy():
    try:
        return jsonify(detector_policy_db.create_policy(request.get_json(silent=True) or {})), 201
    except ValueError as exc:
        return jsonify({'code': 'INVALID_DETECTOR_POLICY', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao criar política de detector')
        return jsonify({'code': 'DETECTOR_POLICY_CREATE_FAILED'}), 500


@detector_policy_bp.route('/<int:policy_id>/activate', methods=['POST'])
def post_activate_policy(policy_id):
    payload = request.get_json(silent=True) or {}
    try:
        policy = detector_policy_db.activate_policy(
            policy_id, payload.get('actor'), payload.get('reason'),
            payload.get('correlation_id'),
        )
        return jsonify(policy)
    except LookupError as exc:
        return jsonify({'code': 'DETECTOR_POLICY_NOT_FOUND', 'error': str(exc)}), 404
    except ValueError as exc:
        return jsonify({'code': 'INVALID_DETECTOR_POLICY_TRANSITION', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao ativar política de detector')
        return jsonify({'code': 'DETECTOR_POLICY_ACTIVATION_FAILED'}), 500
