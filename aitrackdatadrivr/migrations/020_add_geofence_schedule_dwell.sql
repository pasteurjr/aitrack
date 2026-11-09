-- UI-3.9: estado de permanência e evento temporal de cerca.
ALTER TABLE monitoramento.geofence_target_states
  ADD COLUMN IF NOT EXISTS violation_started_at DATETIME(6) NULL
    AFTER last_transition_at,
  ADD COLUMN IF NOT EXISTS dwell_notified_at DATETIME(6) NULL
    AFTER violation_started_at;

ALTER TABLE monitoramento.geofence_events
  MODIFY event_type ENUM('geofence_entry','geofence_exit','geofence_dwell') NOT NULL,
  MODIFY crossing_direction ENUM('outside_to_inside','inside_to_outside') NULL;
