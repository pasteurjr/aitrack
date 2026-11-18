"""API de solicitação/listagem de comandos comprovados."""

import logging
from flask import Blueprint, jsonify, request

from . import device_command_db


device_command_bp = Blueprint('device_commands', __name__, url_prefix='/api/vehicles')
logger = logging.getLogger(__name__)


@device_command_bp.route('/<int:vehicle_id>/commands', methods=['GET'])
def get_commands(vehicle_id):
    try:
        limit = int(request.args.get('limit', 50))
        commands = device_command_db.list_commands(vehicle_id, limit)
        return jsonify({
            'schema_version': 'device-commands.v1',
            'count': len(commands),
            'commands': commands,
        })
    except (TypeError, ValueError, device_command_db.CommandError) as exc:
        return jsonify({'code': 'INVALID_COMMAND_QUERY', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao listar comandos do veículo %s', vehicle_id)
        return jsonify({'code': 'COMMAND_LIST_FAILED'}), 500


@device_command_bp.route('/<int:vehicle_id>/commands', methods=['POST'])
def post_command(vehicle_id):
    try:
        result = device_command_db.create_command(vehicle_id, request.get_json(silent=True) or {})
        return jsonify(result), 200 if result.get('idempotent') else 201
    except device_command_db.CommandUnsupported as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 409
    except device_command_db.CommandConflict as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 409
    except device_command_db.CommandError as exc:
        return jsonify({'code': exc.code, 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao solicitar comando para veículo %s', vehicle_id)
        return jsonify({'code': 'COMMAND_CREATE_FAILED'}), 500
