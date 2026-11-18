"""API de configuração versionada dos agentes."""

import logging
from flask import Blueprint, jsonify, request

from . import agent_config_db


agent_config_bp = Blueprint('agent_configurations', __name__, url_prefix='/api/agent-configurations')
logger = logging.getLogger(__name__)


@agent_config_bp.route('', methods=['GET'])
def get_configurations():
    try:
        configurations = agent_config_db.list_configurations(
            request.args.get('agent_key'), request.args.get('status'),
        )
        return jsonify({
            'schema_version': 'agent-configurations.v1',
            'count': len(configurations),
            'configurations': configurations,
        })
    except ValueError as exc:
        return jsonify({'code': 'INVALID_AGENT_CONFIG_QUERY', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao listar configurações de agente')
        return jsonify({'code': 'AGENT_CONFIGURATIONS_UNAVAILABLE'}), 500


@agent_config_bp.route('', methods=['POST'])
def post_configuration():
    try:
        return jsonify(agent_config_db.create_configuration(request.get_json(silent=True) or {})), 201
    except LookupError as exc:
        return jsonify({'code': 'AGENT_NOT_FOUND', 'error': str(exc)}), 404
    except ValueError as exc:
        return jsonify({'code': 'INVALID_AGENT_CONFIGURATION', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao criar configuração de agente')
        return jsonify({'code': 'AGENT_CONFIGURATION_CREATE_FAILED'}), 500


@agent_config_bp.route('/<int:config_id>/activate', methods=['POST'])
def post_activate_configuration(config_id):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(agent_config_db.activate_configuration(
            config_id, payload.get('actor'), payload.get('reason'),
            payload.get('correlation_id'),
        ))
    except LookupError as exc:
        return jsonify({'code': 'AGENT_CONFIGURATION_NOT_FOUND', 'error': str(exc)}), 404
    except ValueError as exc:
        return jsonify({'code': 'INVALID_AGENT_CONFIGURATION_TRANSITION', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao ativar configuração de agente')
        return jsonify({'code': 'AGENT_CONFIGURATION_ACTIVATION_FAILED'}), 500
