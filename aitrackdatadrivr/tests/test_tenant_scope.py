from pathlib import Path

import pytest
from flask import Flask, g

from server.geofence_db import _where_clause as geofence_where
from server.incident_db import _where_clause as incident_where
from server.tenant_scope import TenantContextMissing, current_tenant_id, trusted_actor


def test_tenant_context_comes_from_authenticated_principal():
    app = Flask(__name__)
    with app.test_request_context('/api/incidents'):
        g.auth = {
            'tenant_id': 41,
            'user_public_id': 'user-public',
            'display_name': 'Operadora',
        }
        assert current_tenant_id() == 41
        assert trusted_actor() == {
            'type': 'human', 'id': 'user-public', 'name': 'Operadora',
        }


def test_missing_tenant_fails_closed_in_request():
    app = Flask(__name__)
    with app.test_request_context('/api/incidents'):
        with pytest.raises(TenantContextMissing):
            current_tenant_id()


@pytest.mark.parametrize('builder', [incident_where, geofence_where])
def test_list_filters_always_prefix_tenant_when_supplied(builder):
    sql, params = builder({}, tenant_id=77)
    assert 'tenant_id = %s' in sql
    assert params == [77]


def test_tenant_migration_owns_operational_roots_and_source_bindings():
    migration = Path(__file__).parents[1] / 'migrations' / '064_create_tenant_scope.sql'
    sql = migration.read_text(encoding='utf-8')
    for table in ('incidents', 'geofences', 'routes', 'agent_definitions',
                  'report_definitions', 'report_runs'):
        assert f'ALTER TABLE monitoramento.{table} ADD COLUMN IF NOT EXISTS tenant_id' in sql
        assert f'ALTER TABLE monitoramento.{table} MODIFY tenant_id' in sql
    assert 'tenant_source_bindings' in sql
    assert 'UNIQUE KEY uq_tenant_source_external' in sql
