-- UI-3.8: estado persistente e eventos confirmados de cruzamento de cercas.
CREATE TABLE IF NOT EXISTS monitoramento.geofence_target_states (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id BIGINT UNSIGNED NOT NULL,
  subject_type ENUM('vehicle','driver') NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  stable_state ENUM('unknown','inside','outside') NOT NULL DEFAULT 'unknown',
  pending_state ENUM('inside','outside') NULL,
  pending_samples SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  last_signed_distance_m DECIMAL(12,3) NULL,
  last_latitude DECIMAL(10,7) NULL,
  last_longitude DECIMAL(10,7) NULL,
  last_accuracy_m DECIMAL(8,2) NULL,
  last_source ENUM('tracker','dirijabem') NULL,
  last_observed_at DATETIME(6) NULL,
  last_transition_at DATETIME(6) NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_geofence_state_vehicle (assignment_id, vehicle_id),
  UNIQUE KEY uk_geofence_state_driver (assignment_id, driver_id),
  KEY idx_geofence_state_observed (last_observed_at),
  CONSTRAINT chk_geofence_state_subject CHECK (
    (subject_type = 'vehicle' AND vehicle_id IS NOT NULL AND driver_id IS NULL)
    OR
    (subject_type = 'driver' AND driver_id IS NOT NULL AND vehicle_id IS NULL)
  ),
  CONSTRAINT fk_geofence_state_assignment
    FOREIGN KEY (assignment_id) REFERENCES monitoramento.geofence_assignments(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_state_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_state_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.geofence_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  assignment_id BIGINT UNSIGNED NOT NULL,
  geofence_id BIGINT UNSIGNED NOT NULL,
  geometry_version_id BIGINT UNSIGNED NOT NULL,
  source_code ENUM('tracker','dirijabem') NOT NULL,
  event_type ENUM('geofence_entry','geofence_exit') NOT NULL,
  crossing_direction ENUM('outside_to_inside','inside_to_outside') NOT NULL,
  rule_applied ENUM('allowed','forbidden') NOT NULL,
  subject_type ENUM('vehicle','driver') NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  accuracy_m DECIMAL(8,2) NULL,
  signed_distance_m DECIMAL(12,3) NOT NULL,
  observed_at DATETIME(6) NOT NULL,
  details_json LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_geofence_events_public_id (public_id),
  KEY idx_geofence_events_timeline (observed_at, id),
  KEY idx_geofence_events_fence (geofence_id, observed_at),
  KEY idx_geofence_events_vehicle (vehicle_id, observed_at),
  KEY idx_geofence_events_driver (driver_id, observed_at),
  CONSTRAINT chk_geofence_event_subject CHECK (
    (subject_type = 'vehicle' AND vehicle_id IS NOT NULL AND driver_id IS NULL)
    OR
    (subject_type = 'driver' AND driver_id IS NOT NULL AND vehicle_id IS NULL)
  ),
  CONSTRAINT chk_geofence_event_details CHECK (
    details_json IS NULL OR JSON_VALID(details_json)
  ),
  CONSTRAINT fk_geofence_event_assignment
    FOREIGN KEY (assignment_id) REFERENCES monitoramento.geofence_assignments(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_event_geofence
    FOREIGN KEY (geofence_id) REFERENCES monitoramento.geofences(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_event_geometry
    FOREIGN KEY (geometry_version_id) REFERENCES monitoramento.geofence_versions(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_event_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_event_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
