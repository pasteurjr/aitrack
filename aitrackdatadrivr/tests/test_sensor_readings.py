from datetime import datetime
from pathlib import Path
import re

import pytest
from flask import Flask

from server import sensor_db
from server import db_handler
from server import sensor_api


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '024_create_sensor_readings.sql'
CLOCK_SKEW_MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '026_allow_sensor_clock_skew.sql'


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.rowcount = 0
        self._reading_keys = set()
        self._selected_sensor_id = 99
        self.lastrowid = 1000

    def execute(self, sql, params=None):
        params = tuple(params or ())
        self.statements.append((sql, params))
        if 'SELECT id FROM monitoramento.sensors' in sql:
            self._selected_sensor_id = abs(hash(params[2])) % 10000 + 1
            self.rowcount = 1
        elif 'INSERT IGNORE INTO monitoramento.sensor_readings' in sql:
            key = (params[0], params[6])
            self.rowcount = 0 if key in self._reading_keys else 1
            self._reading_keys.add(key)
            if self.rowcount:
                self.lastrowid += 1
        else:
            self.rowcount = 1

    def fetchone(self):
        return {'id': self._selected_sensor_id}


@pytest.fixture(autouse=True)
def isolate_power_detector(monkeypatch):
    monkeypatch.setattr(
        sensor_db.power_detector, 'evaluate_external_voltage',
        lambda *_args, **_kwargs: [],
    )


def packet(protocol='maxtrack'):
    return {
        'protocol': protocol,
        'device_id': 'SIM-1000',
        'timestamp': '2026-11-17T15:00:00',
        'latitude': -23.5505,
        'longitude': -46.6333,
        'speed': 42.5,
        'heading': 180,
        'ignition': True,
        'battery_voltage': 12.7,
        'gps_status': True,
        'panic': False,
        'altitude': None,
    }


def confirmed():
    codes = ('position', 'speed', 'heading', 'ignition', 'external_voltage', 'gps_valid')
    return {
        code: {'id': index, 'capability_code': code, 'unit': None}
        for index, code in enumerate(codes, 1)
    }


def test_migration_models_source_quality_times_and_idempotency():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.sensors' in sql
    assert 'monitoramento.sensor_readings' in sql
    assert "enum('valid','invalid','estimated','unknown')" in sql
    assert 'observed_at datetime(6) not null' in sql
    assert 'received_at datetime(6) not null' in sql
    assert 'correlation_id varchar(100) not null' in sql
    assert 'unique key uq_sensor_reading_correlation' in sql
    assert 'json_valid(value_json)' in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


def test_tracker_packet_persists_only_confirmed_typed_readings(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(sensor_db, '_resolve_vehicle_id', lambda *_args: 123)
    monkeypatch.setattr(sensor_db, '_confirmed_capabilities', lambda *_args: confirmed())

    inserted = sensor_db.persist_tracker_readings(
        cursor,
        tracker_vehicle_id=10,
        location_id=500,
        data=packet(),
        received_at=datetime(2026, 11, 17, 15, 0, 1),
    )

    reading_params = [
        params for sql, params in cursor.statements
        if 'INSERT IGNORE INTO monitoramento.sensor_readings' in sql
    ]
    assert inserted == 6
    assert len(reading_params) == 6
    assert all(params[4] == datetime(2026, 11, 17, 15, 0) for params in reading_params)
    assert all(params[5] == datetime(2026, 11, 17, 15, 0, 1) for params in reading_params)
    assert all(params[6] == 'tracker:10:location:500' for params in reading_params)
    assert all('panic' not in params[2] for params in reading_params)
    assert any(
        'INSERT INTO monitoramento.integration_health' in sql
        for sql, _params in cursor.statements
    )


def test_repeated_correlation_is_idempotent(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(sensor_db, '_resolve_vehicle_id', lambda *_args: None)
    monkeypatch.setattr(sensor_db, '_confirmed_capabilities', lambda *_args: confirmed())
    kwargs = {
        'tracker_vehicle_id': 10,
        'location_id': 501,
        'data': packet(),
        'received_at': datetime(2026, 11, 17, 15, 0, 1),
    }

    assert sensor_db.persist_tracker_readings(cursor, **kwargs) == 6
    assert sensor_db.persist_tracker_readings(cursor, **kwargs) == 0


def test_new_external_voltage_reading_calls_detector_once(monkeypatch):
    cursor = FakeCursor()
    calls = []
    monkeypatch.setattr(sensor_db, '_resolve_vehicle_id', lambda *_args: 123)
    monkeypatch.setattr(sensor_db, '_confirmed_capabilities', lambda *_args: confirmed())
    monkeypatch.setattr(
        sensor_db.power_detector, 'evaluate_external_voltage',
        lambda _cursor, **kwargs: calls.append(kwargs),
    )

    sensor_db.persist_tracker_readings(
        cursor, tracker_vehicle_id=10, location_id=503, data=packet(),
        received_at=datetime(2026, 11, 17, 15, 0, 1),
    )

    assert len(calls) == 1
    assert calls[0]['vehicle_id'] == 123
    assert calls[0]['value'] == 12.7


def test_detector_failure_does_not_discard_sensor_readings(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(sensor_db, '_resolve_vehicle_id', lambda *_args: 123)
    monkeypatch.setattr(sensor_db, '_confirmed_capabilities', lambda *_args: confirmed())
    monkeypatch.setattr(
        sensor_db.power_detector, 'evaluate_external_voltage',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('detector down')),
    )

    inserted = sensor_db.persist_tracker_readings(
        cursor, tracker_vehicle_id=10, location_id=504, data=packet(),
        received_at=datetime(2026, 11, 17, 15, 0, 1),
    )

    assert inserted == 6


def test_source_and_receive_times_are_preserved_when_device_clock_is_ahead(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(sensor_db, '_resolve_vehicle_id', lambda *_args: 123)
    monkeypatch.setattr(sensor_db, '_confirmed_capabilities', lambda *_args: confirmed())

    sensor_db.persist_tracker_readings(
        cursor,
        tracker_vehicle_id=10,
        location_id=502,
        data=packet(),
        received_at=datetime(2026, 11, 17, 14, 59, 59),
    )

    params = next(
        params for sql, params in cursor.statements
        if 'INSERT IGNORE INTO monitoramento.sensor_readings' in sql
    )
    assert params[4] == datetime(2026, 11, 17, 15, 0)
    assert params[5] == datetime(2026, 11, 17, 14, 59, 59)


def test_clock_skew_migration_removes_only_invalid_time_order_constraint():
    sql = CLOCK_SKEW_MIGRATION.read_text(encoding='utf-8').lower()

    assert 'alter table monitoramento.sensor_readings' in sql
    assert 'drop constraint chk_sensor_reading_times' in sql
    assert 'drop table' not in sql
    assert 'delete from' not in sql


def test_unsupported_protocol_is_rejected():
    with pytest.raises(ValueError, match='não suportado'):
        sensor_db.persist_tracker_readings(
            FakeCursor(), tracker_vehicle_id=10, location_id=1,
            data=packet(protocol='inventado'),
        )


def test_sensor_failure_is_rolled_back_without_escaping_ingestion(monkeypatch):
    class Connection:
        committed = 0
        rolled_back = 0

        def commit(self):
            self.committed += 1

        def rollback(self):
            self.rolled_back += 1

    connection = Connection()
    monkeypatch.setattr(
        db_handler.sensor_db,
        'persist_tracker_readings',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('sensor db down')),
    )

    result = db_handler._persist_sensor_readings(
        connection, FakeCursor(), 10, 500, packet(),
    )

    assert result == 0
    assert connection.committed == 0
    assert connection.rolled_back == 1


def _sensor_client():
    app = Flask(__name__)
    app.register_blueprint(sensor_api.sensor_bp)
    return app.test_client()


def test_vehicle_sensor_api_returns_real_contract(monkeypatch):
    result = {
        'schema_version': 'vehicle-sensors.v1', 'vehicle': {'id': 12},
        'sources': ['tracker'], 'protocols': ['maxtrack'], 'count': 1,
        'sensors': [{'id': 1, 'capability_code': 'ignition'}],
    }
    monkeypatch.setattr(sensor_api.sensor_db, 'get_vehicle_sensors', lambda vehicle_id: result)

    response = _sensor_client().get('/api/vehicles/12/sensors')

    assert response.status_code == 200
    assert response.get_json() == result


def test_vehicle_sensor_api_has_explicit_not_found_and_failure(monkeypatch):
    monkeypatch.setattr(sensor_api.sensor_db, 'get_vehicle_sensors', lambda _vehicle_id: None)
    missing = _sensor_client().get('/api/vehicles/999/sensors')
    assert missing.status_code == 404
    assert missing.get_json()['code'] == 'VEHICLE_NOT_FOUND'

    monkeypatch.setattr(
        sensor_api.sensor_db, 'get_vehicle_sensors',
        lambda _vehicle_id: (_ for _ in ()).throw(RuntimeError('db down')),
    )
    failure = _sensor_client().get('/api/vehicles/12/sensors')
    assert failure.status_code == 500
    assert failure.get_json()['code'] == 'VEHICLE_SENSORS_UNAVAILABLE'


def test_vehicle_sensor_health_uses_record_age_quality_and_preserves_clock(monkeypatch):
    base = {
        'id': 1, 'source_code': 'tracker', 'protocol_code': 'suntech',
        'device_model': '*', 'external_device_id': 'SIM-1000',
        'capability_code': 'ignition', 'unit': None, 'lifecycle_status': 'active',
        'first_seen_at': datetime(2026, 11, 17, 15, 0),
        'last_seen_at': datetime(2026, 11, 17, 15, 1),
        'support_status': 'confirmed', 'evidence': 'parser',
        'value_type': 'boolean', 'value_json': 'true', 'reading_unit': None,
        'quality': 'valid', 'observed_at': datetime(2026, 11, 17, 18, 1),
        'received_at': datetime(2026, 11, 17, 15, 1),
        'recorded_at': datetime(2026, 11, 17, 15, 1), 'age_seconds': 2,
        'clock_skew_seconds': 10800,
    }
    rows = [
        dict(base),
        dict(base, id=2, capability_code='speed', value_type='number',
             value_json='42.5', age_seconds=121),
        dict(base, id=3, capability_code='gps_valid', quality='invalid'),
        dict(base, id=4, capability_code='altitude', value_json=None,
             value_type=None, quality=None, observed_at=None, received_at=None,
             recorded_at=None, age_seconds=None, clock_skew_seconds=None),
    ]

    class Cursor:
        call = 0
        def execute(self, *_args):
            self.call += 1
        def fetchone(self):
            return {'id': 12, 'public_id': 'vehicle-12', 'placa': 'SIM1000', 'ativo': 1}
        def fetchall(self):
            if self.call == 2:
                return [dict(row) for row in rows]
            return [{
                'protocol_code': 'suntech',
                'capability_code': 'remote_immobilization',
                'support_status': 'unknown',
                'evidence': 'Sem canal de comando',
            }]
        def close(self):
            pass

    class Connection:
        cursor_instance = Cursor()
        def cursor(self, **_kwargs):
            return self.cursor_instance
        def close(self):
            pass

    monkeypatch.setattr(sensor_db, 'get_connection', Connection)

    result = sensor_db.get_vehicle_sensors(12)

    assert [item['health_status'] for item in result['sensors']] == [
        'current', 'stale', 'invalid', 'unavailable',
    ]
    latest = result['sensors'][0]['latest_reading']
    assert latest['value'] is True
    assert latest['received_at'].endswith('-03:00')
    assert latest['observed_at'] == '2026-11-17T18:01:00'
    assert latest['observed_timezone'] == 'unspecified'
    assert latest['clock_skew_seconds'] == 10800
    assert result['confirmed_commands'] == []
    assert result['commands'][0]['support_status'] == 'unknown'
