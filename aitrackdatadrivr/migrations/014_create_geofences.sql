-- UI-3.1: cercas compartilhadas e histórico imutável de geometria.
CREATE TABLE IF NOT EXISTS monitoramento.geofences (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  nome VARCHAR(150) NOT NULL,
  descricao TEXT NULL,
  regra ENUM('allowed','forbidden') NOT NULL,
  status ENUM('draft','active','inactive','archived') NOT NULL DEFAULT 'draft',
  owner_ref VARCHAR(100) NULL,
  criado_por VARCHAR(100) NOT NULL,
  atualizado_por VARCHAR(100) NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_geofences_public_id (public_id),
  KEY idx_geofences_status_rule (status, regra, atualizado_em),
  KEY idx_geofences_owner (owner_ref, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.geofence_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  geofence_id BIGINT UNSIGNED NOT NULL,
  version_number INT UNSIGNED NOT NULL,
  geometry_type ENUM('circle','polygon') NOT NULL,
  geometry GEOMETRY NOT NULL,
  radius_meters DECIMAL(10,2) NULL,
  geometry_hash CHAR(64) NOT NULL,
  change_reason VARCHAR(300) NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  valid_from DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  valid_to DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_geofence_version (geofence_id, version_number),
  UNIQUE KEY uk_geofence_geometry_hash (geofence_id, geometry_hash),
  KEY idx_geofence_versions_validity (geofence_id, valid_from, valid_to),
  SPATIAL KEY idx_geofence_versions_geometry (geometry),
  CONSTRAINT chk_geofence_version_radius CHECK (
    (geometry_type = 'circle' AND radius_meters IS NOT NULL AND radius_meters > 0)
    OR
    (geometry_type = 'polygon' AND radius_meters IS NULL)
  ),
  CONSTRAINT chk_geofence_version_validity CHECK (
    valid_to IS NULL OR valid_to > valid_from
  ),
  CONSTRAINT fk_geofence_versions_geofence
    FOREIGN KEY (geofence_id) REFERENCES monitoramento.geofences(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
