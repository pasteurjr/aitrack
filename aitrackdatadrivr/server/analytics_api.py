from flask import Blueprint, jsonify, request

from .analytics_db import aggregate_behavior, parse_sources
from .analytics_periods import comparison_period, parse_period


analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.get('/behavior')
def behavior():
    try:
        timezone_name = request.args.get('timezone', 'America/Sao_Paulo')
        primary = parse_period(request.args.get('from'), request.args.get('to'), timezone_name)
        comparison = comparison_period(
            primary,
            request.args.get('comparison', 'previous'),
            request.args.get('comparison_from'),
            request.args.get('comparison_to'),
        )
        sources = parse_sources(request.args.get('sources'))
        return jsonify({
            'schema_version': 'behavior-analytics.v1',
            'formula_version': 'event-count.v1',
            'current': aggregate_behavior(primary, sources),
            'comparison': aggregate_behavior(comparison, sources) if comparison else None,
        })
    except ValueError as exc:
        return jsonify({'code': 'INVALID_ANALYTICS_FILTER', 'error': str(exc)}), 400
    except Exception:
        return jsonify({'code': 'ANALYTICS_UNAVAILABLE'}), 500
