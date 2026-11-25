from flask import Blueprint, jsonify, request

from .report_export_db import create_blocked_schedule, create_manual_export


export_bp = Blueprint('report_exports', __name__, url_prefix='/api/report-exports')


@export_bp.post('')
def manual_export():
    try:
        return jsonify(create_manual_export(request.get_json(silent=True) or {})), 201
    except ValueError as exc:
        return jsonify({'code': 'INVALID_EXPORT', 'error': str(exc)}), 400
    except Exception:
        return jsonify({'code': 'EXPORT_UNAVAILABLE'}), 500


@export_bp.post('/schedules')
def schedule():
    try:
        return jsonify(create_blocked_schedule(request.get_json(silent=True) or {})), 201
    except ValueError as exc:
        return jsonify({'code': 'INVALID_EXPORT_SCHEDULE', 'error': str(exc)}), 400
    except Exception:
        return jsonify({'code': 'EXPORT_SCHEDULE_UNAVAILABLE'}), 500
