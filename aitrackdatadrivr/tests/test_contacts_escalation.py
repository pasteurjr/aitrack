from datetime import datetime, timedelta
from pathlib import Path
import pytest
from server.contact_escalation_db import channel_is_eligible, order_candidates, validate_destination_ref

MIGRATION = Path(__file__).resolve().parents[1] / 'migrations' / '048_create_contacts_and_escalation.sql'
NOW = datetime(2026, 11, 19, 23, 20)


def candidate(**overrides):
    row = {'active': True, 'consent_status': 'granted', 'verified_at': NOW,
           'consent_granted_at': NOW-timedelta(days=1), 'consent_revoked_at': None,
           'consent_expires_at': NOW+timedelta(days=1), 'min_severity': 'low',
           'step_order': 1, 'priority': 100, 'channel_id': 1}
    row.update(overrides); return row


def test_consent_must_be_active_verified_and_not_expired_or_revoked():
    assert channel_is_eligible(candidate(), NOW)
    assert not channel_is_eligible(candidate(consent_status='revoked'), NOW)
    assert not channel_is_eligible(candidate(consent_expires_at=NOW-timedelta(seconds=1)), NOW)
    assert not channel_is_eligible(candidate(verified_at=None), NOW)


def test_escalation_order_and_severity_are_deterministic():
    rows = [candidate(channel_id=3,step_order=2), candidate(channel_id=2,priority=20),
            candidate(channel_id=1,priority=10), candidate(channel_id=4,min_severity='critical')]
    assert [x['channel_id'] for x in order_candidates(rows, 'high', NOW)] == [1,2,3]


def test_destination_never_accepts_raw_phone_or_email():
    assert validate_destination_ref('vault:contact/channel/123')
    assert validate_destination_ref('TEST-OWNER-1')
    with pytest.raises(ValueError, match='referência'):
        validate_destination_ref('+5511999999999')
    with pytest.raises(ValueError, match='referência'):
        validate_destination_ref('owner@example.com')


def test_migration_models_consent_roles_order_and_append_only_audit():
    sql = MIGRATION.read_text().lower()
    for token in ('contact_profiles','contact_channels','consent_status','consent_scope','consent_source','escalation_policy_versions','escalation_policy_steps','step_order','contact_audit'):
        assert token in sql
    assert 'contact audit is immutable' in sql and 'contact audit cannot be deleted' in sql
