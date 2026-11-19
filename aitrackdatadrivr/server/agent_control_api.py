import logging
from flask import Blueprint,jsonify,request
from .agent_control_db import AgentControlConflict,get_control,transition_control

agent_control_bp=Blueprint('agent_controls',__name__,url_prefix='/api/agent-controls');logger=logging.getLogger(__name__)

@agent_control_bp.get('/<int:incident_id>')
def get(incident_id):
    try:return jsonify({'schema_version':'agent-incident-control.v1','control':get_control(incident_id)})
    except Exception:return jsonify({'code':'AGENT_CONTROL_UNAVAILABLE'}),500

@agent_control_bp.post('/<int:incident_id>/<command>')
def post(incident_id,command):
    if command not in {'pause','resume','takeover','release'}:return jsonify({'code':'INVALID_AGENT_CONTROL_COMMAND'}),404
    try:return jsonify({'schema_version':'agent-incident-control.v1','control':transition_control(incident_id,command,request.get_json(silent=True) or {})})
    except LookupError as exc:return jsonify({'code':'INCIDENT_NOT_FOUND','error':str(exc)}),404
    except AgentControlConflict as exc:return jsonify({'code':'AGENT_CONTROL_CONFLICT','error':str(exc)}),409
    except ValueError as exc:return jsonify({'code':'INVALID_AGENT_CONTROL','error':str(exc)}),400
    except Exception:
        logger.exception('Falha no controle do agente');return jsonify({'code':'AGENT_CONTROL_FAILED'}),500
