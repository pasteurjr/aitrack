from flask import Blueprint, jsonify, request

from .report_service import generate_behavior_report


report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@report_bp.post('/behavior')
def behavior_report():
    try:
        return jsonify(generate_behavior_report(request.get_json(silent=True) or {})), 201
    except ValueError as exc:
        return jsonify({'code': 'INVALID_REPORT_FILTER', 'error': str(exc)}), 400
    except Exception:
        return jsonify({'code': 'REPORT_UNAVAILABLE'}), 500
