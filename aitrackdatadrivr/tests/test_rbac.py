from pathlib import Path

import pytest

from server.authz import AuthorizationError, require_permission, required_permission


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '063_create_rbac.sql'


@pytest.mark.parametrize(('path', 'method', 'permission'), [
    ('/api/incidents', 'GET', 'incident.read'),
    ('/api/incidents/1/acknowledge', 'POST', 'incident.operate'),
    ('/api/incidents/1/false-positive', 'POST', 'incident.classify'),
    ('/api/geofences', 'POST', 'geofence.manage'),
    ('/api/routes/x', 'PUT', 'route.manage'),
    ('/api/agent-configurations', 'POST', 'agent.configure'),
    ('/api/reports/behavior', 'POST', 'report.read'),
    ('/api/report-exports', 'POST', 'report.export'),
    ('/api/report-exports/schedules', 'POST', 'report.schedule'),
    ('/api/vehicles/1/commands', 'POST', 'device.command.request'),
    ('/api/vehicles/1/commands/x/authorization', 'POST', 'device.command.approve'),
])
def test_route_matrix(path, method, permission):
    assert required_permission(path, method) == permission


def test_authorizer_is_fail_closed():
    require_permission({'permissions': ['incident.read']}, 'incident.read')
    with pytest.raises(AuthorizationError):
        require_permission({'permissions': ['incident.read']}, 'incident.operate')
    assert required_permission('/api/unknown-mutation', 'POST') == 'platform.admin'


def test_schema_has_roles_permissions_and_explicit_assignments():
    sql = MIGRATION.read_text().lower()
    for token in ('auth_permissions', 'auth_roles', 'auth_role_permissions',
                  'auth_membership_roles', 'platform_admin', 'device.command.approve'):
        assert token in sql
