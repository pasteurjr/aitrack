"""API operacional de criação e consulta de cercas eletrônicas."""

import logging

from flask import Blueprint, jsonify, request

from . import geofence_db
from .geofence_geometry import normalize_geometry


geofence_bp = Blueprint('geofences', __name__, url_prefix='/api/geofences')
logger = logging.getLogger(__name__)
VALID_RULES = {'allowed', 'forbidden'}
VALID_STATUS = {'draft', 'active', 'inactive'}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} deve ser inteiro') from exc
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} deve estar entre {minimum} e {maximum}')
    return value


def _optional_text(data, field: str, maximum: int):
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise ValueError(f'{field} deve ter no máximo {maximum} caracteres')
    return value.strip() or None


def _creation_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Corpo JSON é obrigatório')
    nome = data.get('nome')
    if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 150:
        raise ValueError('nome deve ter entre 1 e 150 caracteres')
    regra = data.get('regra')
    if regra not in VALID_RULES:
        raise ValueError('regra deve ser allowed ou forbidden')
    status = data.get('status', 'draft')
    if status not in VALID_STATUS:
        raise ValueError('status deve ser draft, active ou inactive')
    operator = data.get('operator')
    if not isinstance(operator, dict):
        raise ValueError('operator é obrigatório')
    actor_id = str(operator.get('id') or '').strip()
    if not 1 <= len(actor_id) <= 100:
        raise ValueError('operator.id deve ter entre 1 e 100 caracteres')
    change_reason = str(data.get('change_reason') or 'Criação inicial').strip()
    if not 1 <= len(change_reason) <= 300:
        raise ValueError('change_reason deve ter entre 1 e 300 caracteres')
    return {
        'nome': nome.strip(),
        'descricao': _optional_text(data, 'descricao', 5000),
        'regra': regra,
        'status': status,
        'owner_ref': _optional_text(data, 'owner_ref', 100),
        'actor_id': actor_id,
        'change_reason': change_reason,
    }, normalize_geometry(data.get('geometry'))


@geofence_bp.route('', methods=['GET'])
def list_geofences():
    try:
        limit = _bounded_int('limit', 50, 1, 200)
        offset = _bounded_int('offset', 0, 0, 1_000_000)
        status = request.args.get('status')
        regra = request.args.get('regra')
        if status is not None and status not in VALID_STATUS | {'archived'}:
            raise ValueError('status inválido')
        if regra is not None and regra not in VALID_RULES:
            raise ValueError('regra inválida')
        search = request.args.get('search')
        if search is not None:
            search = search.strip()
            if not search or len(search) > 100:
                raise ValueError('search deve ter entre 1 e 100 caracteres')
        fences, total = geofence_db.list_geofences(
            {'status': status, 'regra': regra, 'search': search}, limit, offset,
        )
        return jsonify({
            'schema_version': 'geofence-list.v1',
            'total': total,
            'limit': limit,
            'offset': offset,
            'geofences': fences,
        })
    except ValueError as exc:
        return jsonify({'code': 'INVALID_GEOFENCE_FILTER', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Erro listando cercas')
        return jsonify({
            'code': 'GEOFENCES_UNAVAILABLE',
            'error': 'Não foi possível consultar as cercas',
        }), 500


@geofence_bp.route('/<string:reference>', methods=['GET'])
def get_geofence(reference: str):
    try:
        fence = geofence_db.get_geofence(reference)
        if fence is None:
            return jsonify({
                'code': 'GEOFENCE_NOT_FOUND', 'error': 'Cerca não encontrada',
            }), 404
        return jsonify({'schema_version': 'geofence-detail.v1', 'geofence': fence})
    except Exception:
        logger.exception('Erro consultando cerca %s', reference)
        return jsonify({
            'code': 'GEOFENCE_UNAVAILABLE',
            'error': 'Não foi possível consultar a cerca',
        }), 500


@geofence_bp.route('', methods=['POST'])
def create_geofence():
    try:
        data, geometry = _creation_payload()
        fence = geofence_db.create_geofence(data, geometry)
        return jsonify({'schema_version': 'geofence-detail.v1', 'geofence': fence}), 201
    except ValueError as exc:
        return jsonify({'code': 'INVALID_GEOFENCE', 'error': str(exc)}), 400
    except Exception:
        logger.exception('Erro criando cerca')
        return jsonify({
            'code': 'GEOFENCE_CREATE_FAILED',
            'error': 'Não foi possível criar a cerca',
        }), 500
