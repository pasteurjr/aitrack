from datetime import datetime
from pathlib import Path
import re

import pytest

from server import sensor_db
from server import db_handler


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '024_create_sensor_readings.sql'


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.rowcount = 0
        self._reading_keys = set()
        self._selected_sensor_id = 99

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
        else:
            self.rowcount = 1

    def fetchone(self):
        return {'id': self._selected_sensor_id}


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


def test_future_device_time_is_clamped_to_preserve_receive_invariant(monkeypatch):
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
    assert params[4] == params[5] == datetime(2026, 11, 17, 15, 0)


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
