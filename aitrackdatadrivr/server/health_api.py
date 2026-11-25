from flask import Blueprint, jsonify, request

from .health_service import integration_snapshot, readiness


health_bp = Blueprint('health_details', __name__)


@health_bp.get('/api/health/ready')
def health_ready():
    result = readiness()
    return jsonify(result), (200 if result['status'] == 'ready' else 503)


@health_bp.get('/api/health/integrations')
def health_integrations():
    try:
        limit = int(request.args.get('history_limit', 30))
        if not 0 <= limit <= 100:
            raise ValueError
        return jsonify(integration_snapshot(limit))
    except ValueError:
        return jsonify({'code': 'INVALID_HEALTH_FILTER', 'error': 'history_limit inválido'}), 400
