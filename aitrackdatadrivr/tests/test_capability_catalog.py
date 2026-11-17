from pathlib import Path
import re

from flask import Flask

from server import capability_api


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '023_create_capability_catalog.sql'


def _client():
    app = Flask(__name__)
    app.register_blueprint(capability_api.capability_bp)
    return app.test_client()


def profile(protocol='suntech', model='*', version=1):
    return {
        'id': 1,
        'protocol_code': protocol,
        'device_model': model,
        'version_number': version,
        'status': 'active',
        'capabilities': [{
            'capability_code': 'ignition',
            'capability_type': 'sensor',
            'support_status': 'confirmed',
        }],
    }


def test_migration_is_versioned_additive_and_operational_only():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.capability_profiles' in sql
    assert 'monitoramento.capability_profile_items' in sql
    assert 'unique key uq_capability_profile_version' in sql
    assert "enum('confirmed','unavailable','unknown')" in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql
    assert 'insert into tracker.' not in sql
    assert 'insert into dirijabem.' not in sql


def test_profiles_return_versioned_catalog(monkeypatch):
    monkeypatch.setattr(
        capability_api.capability_db,
        'list_profiles',
        lambda **filters: [profile(protocol=filters['protocol'])],
    )

    response = _client().get('/api/capabilities/profiles?protocol=suntech')

    assert response.status_code == 200
    assert response.get_json()['schema_version'] == 'capability-catalog.v1'
    assert response.get_json()['profiles'][0]['protocol_code'] == 'suntech'


def test_resolve_requires_protocol_and_never_invents_profile(monkeypatch):
    assert _client().get('/api/capabilities/resolve').status_code == 400
    monkeypatch.setattr(capability_api.capability_db, 'resolve_profile', lambda *_args: None)

    response = _client().get('/api/capabilities/resolve?protocol=inexistente')

    assert response.status_code == 404
    assert response.get_json()['code'] == 'CAPABILITY_PROFILE_NOT_FOUND'


def test_resolve_returns_exact_profile(monkeypatch):
    monkeypatch.setattr(
        capability_api.capability_db,
        'resolve_profile',
        lambda protocol, model: profile(protocol, model or '*', version=2),
    )

    response = _client().get('/api/capabilities/resolve?protocol=queclink&device_model=GV300')

    assert response.status_code == 200
    assert response.get_json()['profile']['device_model'] == 'GV300'
    assert response.get_json()['profile']['version_number'] == 2


def test_catalog_failure_is_explicit_and_does_not_fabricate_data(monkeypatch):
    def fail(**_filters):
        raise RuntimeError('database unavailable')

    monkeypatch.setattr(capability_api.capability_db, 'list_profiles', fail)

    response = _client().get('/api/capabilities/profiles')

    assert response.status_code == 500
    assert response.get_json() == {
        'code': 'CAPABILITY_CATALOG_UNAVAILABLE',
        'error': 'Catálogo de capacidades temporariamente indisponível',
    }
