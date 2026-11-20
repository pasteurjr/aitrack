"""Webhook autenticado para eventos do provedor de mensagens sandbox."""

import hashlib
import hmac
import json
import os

from flask import Blueprint, jsonify, request

from .message_event_db import record_message_event

message_event_bp = Blueprint('message_events', __name__, url_prefix='/api/message-events')


def valid_signature(raw, supplied, secret):
    if not secret or not supplied:
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


@message_event_bp.post('/callback')
def callback():
    raw = request.get_data(cache=True)
    secret = os.getenv('MESSAGE_SANDBOX_WEBHOOK_SECRET', '')
    if not valid_signature(raw, request.headers.get('X-Sandbox-Signature'), secret):
        return jsonify({'code': 'INVALID_MESSAGE_EVENT_SIGNATURE'}), 401
    try:
        payload = json.loads(raw)
        return jsonify(record_message_event(payload)), 200
    except json.JSONDecodeError:
        return jsonify({'code': 'INVALID_MESSAGE_EVENT_JSON'}), 400
    except LookupError as exc:
        return jsonify({'code': 'MESSAGE_RECEIPT_NOT_FOUND', 'error': str(exc)}), 404
    except ValueError as exc:
        return jsonify({'code': 'INVALID_MESSAGE_EVENT', 'error': str(exc)}), 400
    except Exception:
        return jsonify({'code': 'MESSAGE_EVENT_FAILED'}), 500
