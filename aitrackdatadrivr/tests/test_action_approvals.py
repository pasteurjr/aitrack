from datetime import datetime,timedelta
from pathlib import Path
import pytest
from server.action_approval_db import ApproverIdentity,validate_approver
from server.action_queue_db import plan_transition

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'049_create_action_approvals.sql'


def approval(**overrides):
    value={'requested_by':'agent-1','required_role':'supervisor','expires_at':datetime.now()+timedelta(minutes=5)};value.update(overrides);return value


def test_approver_must_be_independent_authorized_and_before_expiry():
    validate_approver(ApproverIdentity('human-1','supervisor'),approval())
    validate_approver(ApproverIdentity('admin-1','administrator'),approval())
    with pytest.raises(PermissionError,match='Auto'):validate_approver(ApproverIdentity('agent-1','supervisor'),approval())
    with pytest.raises(PermissionError,match='Papel'):validate_approver(ApproverIdentity('human-1','security_manager'),approval())
    with pytest.raises(ValueError,match='expirada'):validate_approver(ApproverIdentity('human-1','supervisor'),approval(expires_at=datetime.now()-timedelta(seconds=1)))


def test_queue_cannot_claim_until_approved_and_reject_or_expiry_cancel():
    with pytest.raises(ValueError):plan_transition({'status':'awaiting_approval','attempt_count':0,'max_attempts':2},'claim',{'worker_id':'x','lease_seconds':30})
    assert plan_transition({'status':'awaiting_approval'},'approve')['status']=='approved'
    assert plan_transition({'status':'awaiting_approval'},'reject')['status']=='cancelled'
    assert plan_transition({'status':'awaiting_approval'},'expire')['status']=='cancelled'


def test_migration_preserves_reason_role_expiry_version_and_terminal_decision():
    sql=MIGRATION.read_text().lower()
    for token in ('action_approvals','required_role','request_reason','policy_snapshot_json','expires_at','decision_reason','decision_idempotency_key','version'):
        assert token in sql
    assert 'approval identity or terminal decision is immutable' in sql and 'approvals cannot be deleted' in sql
