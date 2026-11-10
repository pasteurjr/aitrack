"""API do ambiente operacional efetivo do processo ativo."""

from flask import Blueprint, jsonify

from .runtime_environment import build_runtime_environment


runtime_bp = Blueprint('runtime', __name__, url_prefix='/api/runtime')


@runtime_bp.route('/environment', methods=['GET'])
def get_runtime_environment():
    response = jsonify(build_runtime_environment())
    response.headers['Cache-Control'] = 'no-store'
    return response
