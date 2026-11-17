"""API somente leitura das capacidades comprovadas por protocolo/modelo."""

import logging

from flask import Blueprint, jsonify, request

from . import capability_db


capability_bp = Blueprint('capabilities', __name__, url_prefix='/api/capabilities')
logger = logging.getLogger(__name__)


@capability_bp.route('/profiles', methods=['GET'])
def get_capability_profiles():
    try:
        profiles = capability_db.list_profiles(
            protocol=request.args.get('protocol'),
            device_model=request.args.get('device_model'),
            active_only=request.args.get('include_inactive', 'false').lower() != 'true',
        )
        return jsonify({
            'schema_version': 'capability-catalog.v1',
            'count': len(profiles),
            'profiles': profiles,
        })
    except Exception:
        logger.exception('Falha ao consultar catálogo de capacidades')
        return jsonify({
            'code': 'CAPABILITY_CATALOG_UNAVAILABLE',
            'error': 'Catálogo de capacidades temporariamente indisponível',
        }), 500


@capability_bp.route('/resolve', methods=['GET'])
def resolve_capability_profile():
    protocol = (request.args.get('protocol') or '').strip().lower()
    if not protocol:
        return jsonify({
            'code': 'PROTOCOL_REQUIRED',
            'error': 'Informe o protocolo para resolver capacidades',
        }), 400
    try:
        profile = capability_db.resolve_profile(protocol, request.args.get('device_model'))
        if profile is None:
            return jsonify({
                'code': 'CAPABILITY_PROFILE_NOT_FOUND',
                'error': 'Nenhum perfil comprovado para o protocolo/modelo informado',
            }), 404
        return jsonify({
            'schema_version': 'capability-catalog.v1',
            'profile': profile,
        })
    except Exception:
        logger.exception('Falha ao resolver perfil de capacidades')
        return jsonify({
            'code': 'CAPABILITY_CATALOG_UNAVAILABLE',
            'error': 'Catálogo de capacidades temporariamente indisponível',
        }), 500
