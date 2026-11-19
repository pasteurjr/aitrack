import logging
from flask import Blueprint,jsonify,request
from .internal_notification_db import create_notification,list_notifications,mark_read
from .action_queue_db import ActionConflict
notification_bp=Blueprint('internal_notifications',__name__,url_prefix='/api/internal-notifications');logger=logging.getLogger(__name__)

@notification_bp.get('')
def get_all():
    try:
        recipient=request.args.get('recipient_ref','operations');unread=request.args.get('unread_only','false').lower()=='true';items=list_notifications(recipient,unread,int(request.args.get('limit',100)));return jsonify({'schema_version':'internal-notifications.v1','count':len(items),'notifications':items})
    except ValueError as exc:return jsonify({'code':'INVALID_NOTIFICATION_QUERY','error':str(exc)}),400
    except Exception:return jsonify({'code':'NOTIFICATIONS_UNAVAILABLE'}),500

@notification_bp.post('')
def create():
    try:return jsonify(create_notification(request.get_json(silent=True) or {})),201
    except ValueError as exc:return jsonify({'code':'INVALID_NOTIFICATION','error':str(exc)}),400
    except Exception:
        logger.exception('Falha criando notificação');return jsonify({'code':'NOTIFICATION_CREATE_FAILED'}),500

@notification_bp.post('/<public_id>/read')
def read(public_id):
    try:return jsonify(mark_read(public_id,request.get_json(silent=True) or {}))
    except LookupError as exc:return jsonify({'code':'NOTIFICATION_NOT_FOUND','error':str(exc)}),404
    except ActionConflict as exc:return jsonify({'code':'NOTIFICATION_CONFLICT','error':str(exc)}),409
    except ValueError as exc:return jsonify({'code':'INVALID_NOTIFICATION_READ','error':str(exc)}),400
    except Exception:return jsonify({'code':'NOTIFICATION_READ_FAILED'}),500
