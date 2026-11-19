from pathlib import Path
import pytest
from flask import Flask
from server.agent_control_db import plan_control
from server.incident_state_machine import plan_transition,InvalidTransition

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'040_create_agent_incident_controls.sql'

def test_control_state_machine_separates_pause_takeover_and_release():
    assert plan_control('active','pause')=='paused';assert plan_control('paused','resume')=='active';assert plan_control('active','takeover')=='human_owned';assert plan_control('human_owned','release')=='active'
    with pytest.raises(ValueError):plan_control('human_owned','pause')

def test_incident_takeover_preserves_open_state_and_assigns_human():
    plan=plan_transition({'status':'waiting_response'},'takeover',{'assigned_type':'human','assigned_to':'operator-1'})
    assert plan['to_status']=='waiting_response' and plan['updates']['assigned_to']=='operator-1'
    with pytest.raises(InvalidTransition):plan_transition({'status':'resolved'},'takeover',{'assigned_type':'human','assigned_to':'x'})

def test_migration_versions_control_and_audit_idempotently():
    sql=MIGRATION.read_text().lower()
    for token in ('agent_incident_controls','control_state','human_owner_id','agent_incident_control_audit','idempotency_key','version'):assert token in sql
    assert 'delete from' not in sql and 'drop table' not in sql
