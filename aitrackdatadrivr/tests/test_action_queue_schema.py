from pathlib import Path
import re

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'042_create_action_queue.sql'

def test_action_queue_contract_has_target_payload_policy_priority_state_attempts_and_idempotency():
    sql=MIGRATION.read_text().lower()
    for token in ('action_queue','action_type','target_type','target_ref','payload_json','policy_snapshot_json','priority','status','attempt_count','max_attempts','idempotency_key','correlation_id','lease_expires_at','action_events','uq_action_queue_idempotency','uq_action_queue_decision_index'):
        assert token in sql
    assert sql.count('on delete restrict')>=4
    assert re.search(r'\bdelete\s+from\b',sql) is None and 'drop table' not in sql

def test_event_timeline_is_append_only_and_json_is_checked():
    sql=MIGRATION.read_text().lower()
    assert 'trg_action_event_immutable_update' in sql and 'trg_action_event_immutable_delete' in sql
    assert 'json_valid(payload_json)' in sql and 'json_valid(policy_snapshot_json)' in sql and 'json_valid(details_json)' in sql
