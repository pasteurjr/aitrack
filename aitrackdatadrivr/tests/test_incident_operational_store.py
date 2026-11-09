from pathlib import Path

from server import incident_db


class IdentityCursor:
    def __init__(self, legacy=None, canonical=None):
        self.legacy = legacy
        self.canonical = canonical
        self.last_sql = ''

    def execute(self, sql, _params=None):
        self.last_sql = ' '.join(sql.split())

    def fetchone(self):
        if 'tracker.veiculo_unificado' in self.last_sql:
            return self.legacy
        if 'monitoramento.veiculos' in self.last_sql:
            return {'id': self.canonical} if self.canonical else None
        return None

    def fetchall(self):
        if 'monitoramento.veiculo_identidades' in self.last_sql:
            return [{'id': self.canonical}] if self.canonical else []
        return []


def test_shadow_mode_maps_legacy_device_to_canonical_vehicle(monkeypatch):
    monkeypatch.setattr(incident_db, 'configured_read_mode', lambda: 'shadow')
    cursor = IdentityCursor(
        legacy={'device_id': 'SIM-1000', 'placa': 'AAA-0001'},
        canonical=42,
    )

    assert incident_db._resolve_input_vehicle_id(cursor, 7) == 42


def test_operational_mode_accepts_only_active_canonical_vehicle(monkeypatch):
    monkeypatch.setattr(incident_db, 'configured_read_mode', lambda: 'operational')

    assert incident_db._resolve_input_vehicle_id(
        IdentityCursor(canonical=42), 42,
    ) == 42


def test_runtime_modules_do_not_write_incidents_to_legacy_schema():
    server_dir = Path(__file__).resolve().parents[1] / 'server'
    for name in ('incident_db.py', 'incident_correlator.py'):
        source = (server_dir / name).read_text(encoding='utf-8')
        assert 'INSERT INTO tracker.incidents' not in source
        assert 'UPDATE tracker.incidents' not in source
        assert 'INSERT INTO tracker.incident_timeline' not in source
