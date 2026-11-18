from pathlib import Path
import re

import pytest
from flask import Flask

from server import power_detector, sensor_api
from server.power_detector import plan_reading, validate_parameters


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '028_create_power_detector.sql'

POWER = {
    'trigger_below_v': 2.0, 'recover_above_v': 8.0,
    'trigger_samples': 2, 'recover_samples': 2, 'cooldown_seconds': 900,
}
LOW = {
    'trigger_above_v': 2.0, 'trigger_below_v': 11.6,
    'recover_above_v': 12.2, 'trigger_samples': 3, 'recover_samples': 3,
}


def test_migration_creates_episodes_and_only_draft_conservative_policies():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert 'monitoramento.detector_signal_state' in sql
    assert 'monitoramento.detector_episodes' in sql
    assert "enum('power_removed','low_external_voltage')" in sql
    assert "'draft',null" in sql
    assert 'trigger_samples' in sql and 'recover_samples' in sql
    assert 'cooldown_seconds' in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


def test_single_low_sample_does_not_open_false_positive():
    first = plan_reading('normal', 0, 0, 0.5, POWER)
    recovered = plan_reading(first.state, first.trigger_count, 0, 12.5, POWER)

    assert first.state == 'trigger_pending' and first.action is None
    assert recovered.state == 'normal' and recovered.action is None


def test_consecutive_power_loss_opens_then_hysteresis_resolves():
    first = plan_reading('normal', 0, 0, 0.5, POWER)
    opened = plan_reading(first.state, first.trigger_count, 0, 0.4, POWER)
    recovering = plan_reading(opened.state, 0, 0, 8.1, POWER)
    bounced = plan_reading(recovering.state, 0, recovering.recovery_count, 0.7, POWER)
    recovering_again = plan_reading(bounced.state, 0, 0, 8.2, POWER)
    resolved = plan_reading(recovering_again.state, 0, recovering_again.recovery_count, 8.3, POWER)

    assert opened.action == 'open' and opened.state == 'active'
    assert recovering.state == 'recovery_pending'
    assert bounced.state == 'active' and bounced.action is None
    assert resolved.action == 'resolve' and resolved.state == 'normal'


def test_low_voltage_requires_three_samples_and_excludes_power_loss_range():
    zero = plan_reading('normal', 0, 0, 0.0, LOW)
    one = plan_reading('normal', 0, 0, 11.0, LOW)
    two = plan_reading(one.state, one.trigger_count, 0, 11.1, LOW)
    three = plan_reading(two.state, two.trigger_count, 0, 11.2, LOW)

    assert zero.state == 'normal'
    assert one.action is None and two.action is None
    assert three.action == 'open'


def test_invalid_hysteresis_or_single_sample_policy_is_rejected():
    with pytest.raises(ValueError, match='Histerese'):
        validate_parameters({**POWER, 'recover_above_v': 1.0})
    with pytest.raises(ValueError, match='duas amostras'):
        validate_parameters({**POWER, 'trigger_samples': 1})


def test_disarmed_vehicle_never_evaluates_policy():
    class Cursor:
        def execute(self, *_args):
            pass
        def fetchone(self):
            return {'state': 'disarmed'}
        def fetchall(self):
            raise AssertionError('políticas não devem ser consultadas')

    result = power_detector.evaluate_external_voltage(
        Cursor(), sensor_id=1, vehicle_id=1, reading_id=1,
        value=0.0, received_at=__import__('datetime').datetime.now(),
    )
    assert result == []


def test_episode_api_exposes_persisted_contract_and_validates_filter(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(sensor_api.sensor_bp)
    expected = {
        'schema_version': 'detector-episodes.v1', 'vehicle_id': 1,
        'count': 1, 'episodes': [{'id': 9, 'episode_type': 'power_removed'}],
    }
    monkeypatch.setattr(sensor_api.power_detector, 'list_episodes', lambda *_args: expected)
    response = app.test_client().get('/api/vehicles/1/detector-episodes?status=open')
    assert response.status_code == 200
    assert response.get_json() == expected

    monkeypatch.setattr(
        sensor_api.power_detector, 'list_episodes',
        lambda *_args: (_ for _ in ()).throw(ValueError('status inválido')),
    )
    invalid = app.test_client().get('/api/vehicles/1/detector-episodes?status=x')
    assert invalid.status_code == 400
