"""Matriz fechada método/rota para autorização humana."""


class AuthorizationError(ValueError):
    pass


def required_permission(path, method):
    method = method.upper()
    if path.startswith('/api/auth/'):
        return None
    if path.startswith('/api/audit'):
        return 'audit.read'
    if path.startswith('/api/health'):
        return 'health.read'
    if path.startswith('/api/report-exports/schedules'):
        return 'report.schedule'
    if path.startswith('/api/report-exports'):
        return 'report.export'
    if path.startswith('/api/reports') or path.startswith('/api/analytics'):
        return 'report.read'
    if '/commands' in path:
        return 'device.command.approve' if 'authorization' in path else 'device.command.request'
    if path.startswith('/api/incidents'):
        if method == 'GET':
            return 'incident.read'
        if any(part in path for part in ('false-positive', 'false-negatives', 'resolve')):
            return 'incident.classify'
        return 'incident.operate'
    if path.startswith('/api/internal-notifications'):
        return 'notification.operate' if method != 'GET' else 'incident.read'
    if path.startswith('/api/geofences'):
        return 'geofence.manage' if method != 'GET' else 'fleet.read'
    if path.startswith('/api/routes'):
        return 'route.manage' if method != 'GET' else 'fleet.read'
    if path.startswith('/api/agent-configurations'):
        return 'agent.configure' if method != 'GET' else 'fleet.read'
    if path.startswith('/api/detector-policies'):
        return 'detector.configure' if method != 'GET' else 'fleet.read'
    if path.startswith('/api/monitors'):
        return 'monitor.manage' if method != 'GET' else 'fleet.read'
    if path.startswith('/api/action'):
        return 'action.reprocess' if 'reprocess' in path else 'action.approve'
    if method == 'GET':
        return 'fleet.read'
    return 'platform.admin'


def require_permission(principal, permission):
    if permission and permission not in set(principal.get('permissions') or []):
        raise AuthorizationError(f'Permissão {permission} é obrigatória')
