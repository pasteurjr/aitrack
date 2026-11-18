"""Consulta operacional do ledger de execuções dos agentes."""

import logging
from flask import Blueprint, jsonify, request

from . import agent_run_db


agent_run_bp = Blueprint('agent_runs', __name__, url_prefix='/api/agent-runs')
logger = logging.getLogger(__name__)


@agent_run_bp.route('', methods=['GET'])
def get_runs():
    try:
        runs = agent_run_db.list_runs(
            request.args.get('agent_key'), request.args.get('status'),
            request.args.get('correlation_id'), int(request.args.get('limit', 100)),
        )
        return jsonify({'schema_version': 'agent-runs.v1', 'count': len(runs), 'runs': runs})
    except (ValueError, agent_run_db.AgentRunError) as exc:
        return jsonify({'code': 'INVALID_AGENT_RUN_QUERY', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Falha ao listar execuções de agente')
        return jsonify({'code': 'AGENT_RUNS_UNAVAILABLE'}), 500
