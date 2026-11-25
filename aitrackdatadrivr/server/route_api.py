from flask import Blueprint,jsonify,request
from . import route_db

route_bp=Blueprint('routes',__name__,url_prefix='/api/routes')

def error(exc):
    if isinstance(exc,LookupError):return jsonify({'code':'ROUTE_NOT_FOUND','error':str(exc)}),404
    if isinstance(exc,route_db.RouteConflict):return jsonify({'code':'ROUTE_CONFLICT','error':str(exc)}),409
    if isinstance(exc,ValueError):return jsonify({'code':'INVALID_ROUTE','error':str(exc)}),400
    return jsonify({'code':'ROUTE_UNAVAILABLE'}),500

@route_bp.get('')
def listing():
    try:
        items=route_db.list_routes(request.args.get('include_archived','false').lower()=='true',int(request.args.get('limit',100)));return jsonify({'schema_version':'routes.v1','count':len(items),'routes':items})
    except Exception as exc:return error(exc)

@route_bp.post('')
def create():
    try:return jsonify({'schema_version':'route.v1','route':route_db.create_route(request.get_json(silent=True) or {})}),201
    except Exception as exc:return error(exc)

@route_bp.get('/<public_id>')
def get(public_id):
    try:
        item=route_db.get_route(public_id)
        if not item:raise LookupError('Rota não encontrada')
        return jsonify({'schema_version':'route.v1','route':item})
    except Exception as exc:return error(exc)

@route_bp.put('/<public_id>')
def update(public_id):
    try:return jsonify({'schema_version':'route.v1','route':route_db.update_route(public_id,request.get_json(silent=True) or {})})
    except Exception as exc:return error(exc)

@route_bp.delete('/<public_id>')
def archive(public_id):
    try:
        data=request.get_json(silent=True) or {};return jsonify(route_db.archive_route(public_id,data.get('expected_version'),data.get('actor_id'),data.get('reason')))
    except Exception as exc:return error(exc)
