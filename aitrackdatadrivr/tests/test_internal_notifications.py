from pathlib import Path
MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'044_create_internal_notifications.sql'
def test_migration_links_notification_action_incident_inbox_and_read_state():
    sql=MIGRATION.read_text().lower()
    for token in ('internal_notifications','action_id','incident_id','recipient_ref','read_at','read_by','read_idempotency_key','uq_internal_notification_action','trg_internal_notification_guard','trg_internal_notification_delete'):assert token in sql
    assert 'delete from' not in sql and 'drop table' not in sql
