from datetime import datetime
from pathlib import Path
import pytest
from server.route_execution_db import parse_instant,plan_execution_transition,validate_window

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'055_create_route_assignments.sql'

def test_window_preserves_instant_across_overnight_and_dst():
    start,end=validate_window('2026-11-24T23:00:00-03:00','2026-11-25T02:00:00-03:00','America/Sao_Paulo')
    assert (end-start).total_seconds()==10800
    dst_start,dst_end=validate_window('2026-11-01T01:30:00-04:00','2026-11-01T01:30:00-05:00','America/New_York')
    assert (dst_end-dst_start).total_seconds()==3600
    with pytest.raises(ValueError,match='fuso'):parse_instant('2026-11-24T10:00:00','start')

def test_execution_state_machine_is_explicit_and_terminal():
    assert plan_execution_transition('scheduled','start')=='active'
    assert plan_execution_transition('active','complete')=='completed'
    with pytest.raises(ValueError):plan_execution_transition('completed','start')
    assert plan_execution_transition('scheduled','expire')=='expired'

def test_migration_freezes_route_version_and_exactly_one_target():
    sql=MIGRATION.read_text().lower()
    for token in ('route_assignments','route_executions','route_execution_timeline','route_version_id','timezone_name','planned_start_at','planned_end_at','idempotency_key'):assert token in sql
    assert '(vehicle_id is null)<>(driver_id is null)' in sql
    assert 'route execution timeline is immutable' in sql
