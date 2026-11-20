from datetime import datetime,time,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from server.action_contact_policy import ContactContext,ContactPolicy,_database_time,evaluate_contact_policy,is_quiet_time

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'053_create_action_contact_policies.sql'
POLICY=ContactPolicy('America/Sao_Paulo',time(20),time(8),3,4,1000,900,2)


def context(**values):
    base={'attempt_count':0,'contacts_today':0,'cost_cents_today':0,'estimated_cost_cents':100,'last_contact_at':None,'consecutive_no_progress':0};base.update(values);return ContactContext(**base)


def test_overnight_quiet_hours_and_timezone_are_enforced():
    assert is_quiet_time(time(23),time(20),time(8)) and is_quiet_time(time(7,59),time(20),time(8))
    assert not is_quiet_time(time(12),time(20),time(8))
    denied=evaluate_contact_policy(POLICY,context(),datetime(2026,11,20,2,tzinfo=timezone.utc))
    allowed=evaluate_contact_policy(POLICY,context(),datetime(2026,11,20,15,tzinfo=timezone.utc))
    assert denied['denial_codes']==['QUIET_HOURS'] and allowed['allowed']
    assert _database_time(timedelta(hours=20))==time(20)


def test_attempt_daily_cost_cooldown_and_no_progress_limits_combine():
    now=datetime(2026,11,20,15,tzinfo=timezone.utc)
    result=evaluate_contact_policy(POLICY,context(attempt_count=3,contacts_today=4,cost_cents_today=950,estimated_cost_cents=100,last_contact_at=now-timedelta(seconds=30),consecutive_no_progress=2),now)
    assert set(result['denial_codes'])=={'ATTEMPT_LIMIT','DAILY_CONTACT_LIMIT','DAILY_COST_LIMIT','COOLDOWN','NO_PROGRESS_LIMIT'}


def test_dst_conversion_uses_zoneinfo_without_naive_local_arithmetic():
    policy=ContactPolicy('America/New_York',time(1,30),time(3,30),3,4,1000,0,2)
    before=evaluate_contact_policy(policy,context(),datetime(2026,3,8,6,15,tzinfo=timezone.utc))
    after=evaluate_contact_policy(policy,context(),datetime(2026,3,8,7,15,tzinfo=timezone.utc))
    assert before['allowed'] and after['denial_codes']==['QUIET_HOURS']


def test_policy_migration_seeds_safe_default_and_audits_every_decision():
    sql=MIGRATION.read_text().lower()
    for token in ('action_contact_policy_versions','action_policy_decisions','quiet_start','quiet_end','timezone_name','max_contacts_per_target_day','max_cost_cents_per_target_day','cooldown_seconds','max_consecutive_no_progress'):
        assert token in sql
    assert 'external-contact-default' in sql and 'action policy decisions are immutable' in sql
