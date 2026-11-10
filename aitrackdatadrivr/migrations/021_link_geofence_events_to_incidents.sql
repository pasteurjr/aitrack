-- UI-3.10: episódio estável e correlação retomável com incidente operacional.
ALTER TABLE monitoramento.geofence_target_states
  ADD COLUMN IF NOT EXISTS violation_episode_id CHAR(36) NULL
    AFTER dwell_notified_at;

ALTER TABLE monitoramento.geofence_events
  ADD COLUMN IF NOT EXISTS violation_episode_id CHAR(36) NULL
    AFTER geometry_version_id,
  ADD COLUMN IF NOT EXISTS context_vehicle_id BIGINT UNSIGNED NULL
    AFTER violation_episode_id,
  ADD COLUMN IF NOT EXISTS incident_id BIGINT UNSIGNED NULL
    AFTER context_vehicle_id,
  ADD COLUMN IF NOT EXISTS correlation_status
    ENUM('pending','correlated','deferred','error') NOT NULL DEFAULT 'pending'
    AFTER incident_id,
  ADD COLUMN IF NOT EXISTS correlation_attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0
    AFTER correlation_status,
  ADD COLUMN IF NOT EXISTS correlation_error VARCHAR(1000) NULL
    AFTER correlation_attempts,
  ADD COLUMN IF NOT EXISTS correlated_at DATETIME(6) NULL
    AFTER correlation_error,
  ADD KEY IF NOT EXISTS idx_geofence_events_incident (incident_id),
  ADD KEY IF NOT EXISTS idx_geofence_events_episode (violation_episode_id),
  ADD KEY IF NOT EXISTS idx_geofence_events_correlation
    (correlation_status, received_at, id),
  ADD KEY IF NOT EXISTS idx_geofence_events_context_vehicle (context_vehicle_id),
  ADD CONSTRAINT fk_geofence_event_incident
    FOREIGN KEY (incident_id) REFERENCES monitoramento.incidents(id)
    ON DELETE RESTRICT,
  ADD CONSTRAINT fk_geofence_event_context_vehicle
    FOREIGN KEY (context_vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT;
