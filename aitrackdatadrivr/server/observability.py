"""Logs JSON e métricas de baixa cardinalidade para o processo Flask."""

from collections import Counter
from datetime import datetime, timezone
import json
import logging
from threading import Lock
from time import perf_counter

from flask import g, jsonify, request

from .health_service import sanitize_reason


LATENCY_BUCKETS_MS = (25, 50, 100, 250, 500, 1000, 2500, 5000)


class MetricsRegistry:
    def __init__(self):
        self._lock = Lock()
        self._requests = Counter()
        self._latency = Counter()

    def observe_http(self, method, route, status, duration_ms):
        key = (str(method).upper(), normalize_route(route), str(int(status)))
        with self._lock:
            self._requests[key] += 1
            for bucket in LATENCY_BUCKETS_MS:
                if duration_ms <= bucket:
                    self._latency[(key, bucket)] += 1
            self._latency[(key, '+Inf')] += 1

    def snapshot(self):
        with self._lock:
            requests = [
                {'method': method, 'route': route, 'status': status, 'count': count}
                for (method, route, status), count in sorted(self._requests.items())
            ]
            latency = [
                {'method': key[0], 'route': key[1], 'status': key[2],
                 'le_ms': bucket, 'count': count}
                for (key, bucket), count in sorted(
                    self._latency.items(), key=lambda item: str(item[0])
                )
            ]
        return {'http_requests_total': requests, 'http_latency_bucket': latency}

    def reset(self):
        with self._lock:
            self._requests.clear(); self._latency.clear()


def normalize_route(route):
    value = str(route or 'unmatched')
    return value if value.startswith('/') and len(value) <= 200 else 'unmatched'


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': sanitize_reason(record.getMessage()),
        }
        for field in ('request_id', 'correlation_id', 'route', 'method', 'status',
                      'duration_ms', 'tenant_id', 'user_public_id'):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(',', ':'), default=str)


REGISTRY = MetricsRegistry()
logger = logging.getLogger('aitrack.http')


def configure_json_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    if not any(isinstance(item.formatter, JsonFormatter) for item in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)


def install_observability(app):
    configure_json_logging()

    @app.before_request
    def start_observation():
        g.observation_started_at = perf_counter()

    @app.after_request
    def finish_observation(response):
        duration_ms = (perf_counter() - getattr(g, 'observation_started_at', perf_counter())) * 1000
        route = request.url_rule.rule if request.url_rule else 'unmatched'
        REGISTRY.observe_http(request.method, route, response.status_code, duration_ms)
        principal = getattr(g, 'auth', {}) or {}
        logger.info('http_request', extra={
            'request_id': getattr(g, 'request_id', None), 'route': normalize_route(route),
            'method': request.method, 'status': response.status_code,
            'duration_ms': round(duration_ms, 3), 'tenant_id': principal.get('tenant_id'),
            'user_public_id': principal.get('user_public_id'),
        })
        return response


def metrics_response():
    return jsonify({
        'schema_version': 'operations-metrics.v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'metrics': REGISTRY.snapshot(),
    })
