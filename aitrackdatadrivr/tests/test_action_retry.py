from pathlib import Path
import pytest
from server.action_retry_db import calculate_backoff
from server.action_queue_db import plan_transition

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'050_create_action_reprocess_audit.sql'


def test_backoff_is_deterministic_exponential_jittered_and_capped():
    values=[calculate_backoff(i,'action-1') for i in range(1,10)]
    assert values==[calculate_backoff(i,'action-1') for i in range(1,10)]
    assert values[0]>=30 and values[1]>=60 and values[2]>=120
    assert values[-1]<=3600 and values==sorted(values)


def test_attempt_limit_forces_dead_letter_instead_of_infinite_retry():
    failed={'status':'failed','attempt_count':3,'max_attempts':3}
    with pytest.raises(ValueError,match='dead_letter'):plan_transition(failed,'retry',{})
    assert plan_transition(failed,'dead_letter',{})['status']=='dead'


def test_reprocess_audit_preserves_original_and_is_append_only():
    sql=MIGRATION.read_text().lower()
    for token in ('action_reprocess_audit','original_action_id','replacement_action_id','actor_id','reason','idempotency_key'):
        assert token in sql
    assert 'reprocess audit is immutable' in sql and 'reprocess audit cannot be deleted' in sql
