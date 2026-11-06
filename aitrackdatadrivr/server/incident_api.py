"""API versionada de consulta e comandos dos incidentes operacionais."""

import logging

from flask import Blueprint, jsonify, request

from . import incident_db
from .incident_state_machine import InvalidTransition


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


def _command_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Corpo JSON é obrigatório')
    expected_version = data.get('expected_version')
    if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
        raise ValueError('expected_version deve ser inteiro positivo')
    idempotency_key = data.get('idempotency_key')
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key.strip()) <= 150:
        raise ValueError('idempotency_key deve ter entre 1 e 150 caracteres')
    operator = data.get('operator')
    if not isinstance(operator, dict):
        raise ValueError('operator é obrigatório')
    operator_id = str(operator.get('id') or '').strip()
    operator_name = str(operator.get('name') or '').strip()
    if not operator_id or len(operator_id) > 100:
        raise ValueError('operator.id deve ter entre 1 e 100 caracteres')
    if not operator_name or len(operator_name) > 150:
        raise ValueError('operator.name deve ter entre 1 e 150 caracteres')
    return data, expected_version, idempotency_key.strip(), {
        'type': 'human', 'id': operator_id, 'name': operator_name,
    }


def _command_error(exc, incident_id: int):
    if isinstance(exc, incident_db.IncidentNotFound):
        return jsonify({'code': 'INCIDENT_NOT_FOUND', 'error': 'Incidente não encontrado'}), 404
    if isinstance(exc, incident_db.IncidentConflict):
        return jsonify({
            'code': 'INCIDENT_VERSION_CONFLICT',
            'error': 'O incidente foi atualizado. Recarregue antes de tentar novamente.',
        }), 409
    if isinstance(exc, InvalidTransition):
        return jsonify({'code': 'INVALID_INCIDENT_TRANSITION', 'error': str(exc)}), 422
    if isinstance(exc, ValueError):
        return jsonify({'code': 'INVALID_INCIDENT_COMMAND', 'error': str(exc)}), 400
    logger.exception('Erro executando comando no incidente %s', incident_id)
    return jsonify({
        'code': 'INCIDENT_COMMAND_UNAVAILABLE',
        'error': 'Não foi possível executar o comando',
    }), 500


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


def _transition_command(incident_id: int, command: str, payload_builder):
    try:
        data, expected_version, idempotency_key, actor = _command_body()
        payload = payload_builder(data, actor)
        incident = incident_db.transition_incident(
            incident_id, command, payload, actor, expected_version, idempotency_key,
        )
        return jsonify({'schema_version': 'incident-command.v1', 'incident': incident})
    except Exception as exc:
        return _command_error(exc, incident_id)


@incident_bp.route('/<int:incident_id>/acknowledge', methods=['POST'])
def acknowledge_incident(incident_id: int):
    return _transition_command(
        incident_id,
        'triage',
        lambda _data, actor: {'summary': f'{actor["name"]} reconheceu o incidente'},
    )


@incident_bp.route('/<int:incident_id>/assume', methods=['POST'])
def assume_incident(incident_id: int):
    return _transition_command(
        incident_id,
        'start_service',
        lambda _data, actor: {
            'assigned_type': 'human',
            'assigned_to': actor['id'],
            'summary': f'{actor["name"]} assumiu o atendimento',
        },
    )


@incident_bp.route('/<int:incident_id>/comments', methods=['POST'])
def comment_incident(incident_id: int):
    try:
        data, expected_version, idempotency_key, actor = _command_body()
        incident = incident_db.add_incident_comment(
            incident_id, data.get('comment'), actor, expected_version, idempotency_key,
        )
        return jsonify({'schema_version': 'incident-command.v1', 'incident': incident})
    except Exception as exc:
        return _command_error(exc, incident_id)
