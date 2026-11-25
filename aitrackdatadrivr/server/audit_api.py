"""Consulta protegida da trilha transversal de auditoria."""

from datetime import datetime
from flask import Blueprint, g, jsonify, request

from .audit_service import list_events


audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit-events')


@audit_bp.get('')
def get_audit_events():
    try:
        limit = int(request.args.get('limit', 100))
        if not 1 <= limit <= 200:
            raise ValueError('limit deve estar entre 1 e 200')
        cursor_id = request.args.get('cursor')
        cursor_id = int(cursor_id) if cursor_id else None
        filters = {
            key: request.args.get(key)
            for key in ('actor_public_id', 'action', 'resource_type', 'correlation_id')
        }
        for key in ('from', 'to'):
            value = request.args.get(key)
            if value:
                filters[key] = datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        events, next_cursor = list_events(g.auth['tenant_id'], filters, limit, cursor_id)
        return jsonify({
            'schema_version': 'audit-events.v1', 'events': events,
            'next_cursor': next_cursor,
        })
    except (ValueError, TypeError):
        return jsonify({'code': 'INVALID_AUDIT_FILTER', 'error': 'Filtro de auditoria inválido'}), 400
