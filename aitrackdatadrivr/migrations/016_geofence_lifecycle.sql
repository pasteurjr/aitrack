-- UI-3.6: ciclo de vida auditável e reuso seguro de geometrias anteriores.
ALTER TABLE monitoramento.geofence_versions
  DROP INDEX IF EXISTS uk_geofence_geometry_hash,
  ADD KEY idx_geofence_geometry_hash (geofence_id, geometry_hash);

CREATE TABLE IF NOT EXISTS monitoramento.geofence_audit_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  geofence_id BIGINT UNSIGNED NOT NULL,
  action ENUM('created','updated','geometry_updated','archived') NOT NULL,
  from_version INT UNSIGNED NULL,
  to_version INT UNSIGNED NOT NULL,
  actor VARCHAR(100) NOT NULL,
  reason VARCHAR(300) NOT NULL,
  details_json LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_geofence_audit_timeline (geofence_id, created_at, id),
  CONSTRAINT chk_geofence_audit_details CHECK (
    details_json IS NULL OR JSON_VALID(details_json)
  ),
  CONSTRAINT fk_geofence_audit_geofence
    FOREIGN KEY (geofence_id) REFERENCES monitoramento.geofences(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
