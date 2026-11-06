"""API versionada de leitura dos incidentes operacionais."""

import logging

from flask import Blueprint, jsonify, request

from . import incident_db


incident_bp = Blueprint('incidents', __name__, url_prefix='/api/incidents')
logger = logging.getLogger(__name__)

VALID_STATUS = {
    'new', 'triage', 'in_progress', 'waiting_response',
    'escalated', 'resolved', 'closed',
}
VALID_SEVERITY = {'low', 'medium', 'high', 'critical'}
VALID_SOURCE = {'tracker', 'dirijabem', 'fused', 'system'}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = request.args.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f'{name} deve ser inteiro') from exc
    if value < minimum or value > maximum:
        raise ValueError(f'{name} deve estar entre {minimum} e {maximum}')
    return value


def _optional_positive_int(name: str):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f'{name} deve ser inteiro positivo') from exc
    if value <= 0:
        raise ValueError(f'{name} deve ser inteiro positivo')
    return value


def _enum_filter(name: str, valid_values):
    value = request.args.get(name)
    if value is not None and value not in valid_values:
        raise ValueError(f'{name} inválido')
    return value


def _boolean_filter(name: str, default: bool = False) -> bool:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    raise ValueError(f'{name} deve ser booleano')


@incident_bp.route('', methods=['GET'])
def list_incidents():
    try:
        limit = _bounded_int('limit', 50, 1, 200)
        offset = _bounded_int('offset', 0, 0, 1_000_000)
        assigned_to = request.args.get('assigned_to')
        if assigned_to is not None:
            assigned_to = assigned_to.strip()
            if not assigned_to or len(assigned_to) > 100:
                raise ValueError('assigned_to deve ter entre 1 e 100 caracteres')
        filters = {
            'status': _enum_filter('status', VALID_STATUS),
            'severity': _enum_filter('severity', VALID_SEVERITY),
            'primary_source': _enum_filter('primary_source', VALID_SOURCE),
            'vehicle_id': _optional_positive_int('vehicle_id'),
            'monitor_id': _optional_positive_int('monitor_id'),
            'assigned_to': assigned_to,
            'open_only': _boolean_filter('open_only'),
        }
        incidents, total = incident_db.list_incidents(filters, limit, offset)
        return jsonify({
            'schema_version': 'incident-list.v1',
            'total': total,
            'limit': limit,
            'offset': offset,
            'incidents': incidents,
        })
    except ValueError as exc:
        return jsonify({'code': 'INVALID_INCIDENT_FILTER', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Erro listando incidentes')
        return jsonify({
            'code': 'INCIDENTS_UNAVAILABLE',
            'error': 'Não foi possível consultar os incidentes',
        }), 500


@incident_bp.route('/<int:incident_id>', methods=['GET'])
def get_incident(incident_id: int):
    try:
        timeline_limit = _bounded_int('timeline_limit', 200, 1, 1000)
        incident = incident_db.get_incident(incident_id, timeline_limit)
        if incident is None:
            return jsonify({
                'code': 'INCIDENT_NOT_FOUND',
                'error': 'Incidente não encontrado',
            }), 404
        return jsonify({
            'schema_version': 'incident-detail.v1',
            'incident': incident,
        })
    except ValueError as exc:
        return jsonify({'code': 'INVALID_INCIDENT_FILTER', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Erro consultando incidente %s', incident_id)
        return jsonify({
            'code': 'INCIDENT_UNAVAILABLE',
            'error': 'Não foi possível consultar o incidente',
        }), 500
