from pathlib import Path
import pytest
from server.action_queue_db import plan_transition

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'043_secure_action_queue_transitions.sql'
def action(**values):
    result={'status':'pending','attempt_count':0,'max_attempts':2};result.update(values);return result

def test_state_machine_covers_approval_delivery_response_failure_retry_and_terminal():
    assert plan_transition(action(),'request_approval',{})['status']=='awaiting_approval'
    assert plan_transition(action(status='awaiting_approval'),'approve',{})['status']=='approved'
    assert plan_transition(action(status='approved'),'claim',{'worker_id':'worker-1','lease_seconds':30})['attempt_count']==1
    assert plan_transition(action(status='claimed',attempt_count=1),'mark_sent',{})['status']=='sent'
    assert plan_transition(action(status='sent'),'mark_delivered',{})['status']=='delivered'
    assert plan_transition(action(status='delivered'),'mark_responded',{})['status']=='responded'
    assert plan_transition(action(status='claimed'),'fail',{'error_code':'x'})['status']=='failed'
    assert plan_transition(action(status='failed',attempt_count=1),'retry',{})['status']=='pending'

def test_invalid_retry_and_terminal_reentry_are_rejected():
    with pytest.raises(ValueError,match='dead_letter'):plan_transition(action(status='failed',attempt_count=2),'retry',{})
    with pytest.raises(ValueError):plan_transition(action(status='responded'),'retry',{})
    with pytest.raises(ValueError,match='error_code'):plan_transition(action(status='claimed'),'fail',{})

def test_migration_guards_identity_final_state_and_delete():
    sql=MIGRATION.read_text().lower();assert 'trg_action_queue_guard_update' in sql and 'trg_action_queue_guard_delete' in sql
    assert "old.status in ('responded','dead','cancelled','simulated')" in sql
