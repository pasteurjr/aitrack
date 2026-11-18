from datetime import datetime, timedelta
from pathlib import Path
import re

import pytest

from server.offline_detector import (
    context_threshold,
    plan_check,
    suppression_reason,
    validate_parameters,
)


MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '029_create_contextual_offline_detector.sql'
RUNNER = Path(__file__).resolve().parents[1] / 'run.py'
PARAMS = {
    'expected_interval_seconds': 5,
    'moving_grace_seconds': 60,
    'ignition_grace_seconds': 120,
    'idle_grace_seconds': 600,
    'integration_outage_seconds': 120,
    'trigger_checks': 2,
    'recovery_checks': 2,
}


def test_migration_models_context_health_state_and_draft_policy():
    sql = MIGRATION.read_text(encoding='utf-8').lower()

    assert "'offline'" in sql
    assert 'monitoramento.integration_health' in sql
    assert 'monitoramento.vehicle_monitoring_context' in sql
    assert 'monitoramento.offline_detector_state' in sql
    assert "'vehicle-offline',1,'offline','position','source','tracker'" in sql
    assert "'draft',null" in sql
    assert re.search(r'\bdelete\s+from\b', sql) is None
    assert 'drop table' not in sql


def test_runtime_starts_and_supervises_offline_worker():
    source = RUNNER.read_text(encoding='utf-8')
    assert 'run_offline_detector' in source
    assert 'offline_detector_thread.start()' in source
    assert 'offline_detector_thread.is_alive()' in source


def test_context_uses_shorter_window_for_moving_and_ignition():
    assert context_threshold(PARAMS, ignition=True, speed=20) == ('moving', 60)
    assert context_threshold(PARAMS, ignition=True, speed=0) == ('ignition_on', 120)
    assert context_threshold(PARAMS, ignition=False, speed=0) == ('idle_or_unknown', 600)
    assert context_threshold(PARAMS, ignition=None, speed=None) == ('idle_or_unknown', 600)


def test_offline_requires_two_checks_and_recovery_survives_bounce():
    suspect = plan_check('normal', 0, 0, stale=True, parameters=PARAMS)
    opened = plan_check(suspect.state, suspect.stale_checks, 0, stale=True, parameters=PARAMS)
    recovering = plan_check(opened.state, 0, 0, stale=False, parameters=PARAMS)
    bounced = plan_check(recovering.state, 0, recovering.recovery_checks, stale=True, parameters=PARAMS)
    recovering_again = plan_check(bounced.state, 0, 0, stale=False, parameters=PARAMS)
    resolved = plan_check(recovering_again.state, 0, recovering_again.recovery_checks, stale=False, parameters=PARAMS)

    assert suspect.action is None
    assert opened.action == 'open'
    assert recovering.state == 'recovery_pending'
    assert bounced.state == 'offline' and bounced.action is None
    assert resolved.action == 'resolve'


def test_fresh_check_cancels_single_suspect_without_false_positive():
    suspect = plan_check('normal', 0, 0, stale=True, parameters=PARAMS)
    normal = plan_check(suspect.state, suspect.stale_checks, 0, stale=False, parameters=PARAMS)
    assert normal.state == 'normal' and normal.action is None


def test_suppressions_distinguish_vehicle_integration_and_maintenance():
    now = datetime(2026, 11, 17, 21, 0)
    common = {
        'integration_status': 'healthy', 'integration_last_success': now,
        'maintenance_until': None, 'now': now, 'parameters': PARAMS,
    }
    assert suppression_reason(security_state='disarmed', **common) == 'vehicle_disarmed'
    assert suppression_reason(
        security_state='armed', **{**common, 'integration_last_success': now - timedelta(seconds=121)},
    ) == 'integration_outage'
    assert suppression_reason(
        security_state='armed', **{**common, 'integration_status': 'outage'},
    ) == 'integration_outage'
    assert suppression_reason(
        security_state='armed', **{**common, 'maintenance_until': now + timedelta(hours=1)},
    ) == 'maintenance'
    assert suppression_reason(security_state='armed', **common) is None


def test_invalid_windows_and_permissive_check_count_are_rejected():
    with pytest.raises(ValueError, match='crescer'):
        validate_parameters({**PARAMS, 'idle_grace_seconds': 30})
    with pytest.raises(ValueError, match='duas verificações'):
        validate_parameters({**PARAMS, 'trigger_checks': 1})
