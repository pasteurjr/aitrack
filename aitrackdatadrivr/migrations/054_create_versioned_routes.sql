-- UI-7.1: rotas operacionais unificadas e versões geométricas imutáveis.
CREATE TABLE IF NOT EXISTS monitoramento.routes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  name VARCHAR(150) NOT NULL,
  description VARCHAR(1000) NULL,
  status ENUM('active','archived') NOT NULL DEFAULT 'active',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_route_public(public_id), KEY idx_route_status(status,updated_at,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.route_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  route_id BIGINT UNSIGNED NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  geometry_json LONGTEXT NOT NULL,
  geometry_sha256 CHAR(64) NOT NULL,
  corridor_meters DECIMAL(10,2) NOT NULL,
  length_meters DECIMAL(14,2) NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_route_version(route_id,version_no),
  KEY idx_route_version_hash(geometry_sha256),
  CONSTRAINT fk_route_version_route FOREIGN KEY(route_id) REFERENCES monitoramento.routes(id) ON DELETE RESTRICT,
  CONSTRAINT chk_route_geometry CHECK(JSON_VALID(geometry_json)),
  CONSTRAINT chk_route_corridor CHECK(corridor_meters BETWEEN 5 AND 5000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.route_audit_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  route_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  snapshot_json LONGTEXT NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), KEY idx_route_audit(route_id,occurred_at,id),
  CONSTRAINT fk_route_audit_route FOREIGN KEY(route_id) REFERENCES monitoramento.routes(id) ON DELETE RESTRICT,
  CONSTRAINT chk_route_audit_snapshot CHECK(JSON_VALID(snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_route_version_update BEFORE UPDATE ON monitoramento.route_versions
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='route versions are immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_route_version_delete BEFORE DELETE ON monitoramento.route_versions
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='route versions cannot be deleted'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_route_audit_update BEFORE UPDATE ON monitoramento.route_audit_log
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='route audit is immutable'; END$$
DELIMITER ;
