-- UI-7.2: atribuições unificadas e execuções com versão congelada.
CREATE TABLE IF NOT EXISTS monitoramento.route_assignments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  route_version_id BIGINT UNSIGNED NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  timezone_name VARCHAR(100) NOT NULL,
  valid_from DATETIME(6) NOT NULL,
  valid_until DATETIME(6) NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_route_assignment_public(public_id),
  KEY idx_route_assignment_vehicle(vehicle_id,active,valid_from,valid_until),
  KEY idx_route_assignment_driver(driver_id,active,valid_from,valid_until),
  CONSTRAINT fk_route_assignment_version FOREIGN KEY(route_version_id) REFERENCES monitoramento.route_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_route_assignment_vehicle FOREIGN KEY(vehicle_id) REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT fk_route_assignment_driver FOREIGN KEY(driver_id) REFERENCES monitoramento.motoristas(id) ON DELETE RESTRICT,
  CONSTRAINT chk_route_assignment_target CHECK((vehicle_id IS NULL)<>(driver_id IS NULL)),
  CONSTRAINT chk_route_assignment_interval CHECK(valid_until>valid_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.route_executions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  assignment_id BIGINT UNSIGNED NOT NULL,
  route_version_id BIGINT UNSIGNED NOT NULL,
  planned_start_at DATETIME(6) NOT NULL,
  planned_end_at DATETIME(6) NOT NULL,
  status ENUM('scheduled','active','completed','cancelled','expired','failed') NOT NULL DEFAULT 'scheduled',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  idempotency_key VARCHAR(150) NOT NULL,
  started_at DATETIME(6) NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_route_execution_public(public_id),
  UNIQUE KEY uq_route_execution_idempotency(idempotency_key),
  KEY idx_route_execution_state(status,planned_start_at,planned_end_at,id),
  CONSTRAINT fk_route_execution_assignment FOREIGN KEY(assignment_id) REFERENCES monitoramento.route_assignments(id) ON DELETE RESTRICT,
  CONSTRAINT fk_route_execution_version FOREIGN KEY(route_version_id) REFERENCES monitoramento.route_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_route_execution_interval CHECK(planned_end_at>planned_start_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.route_execution_timeline (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  execution_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  from_status VARCHAR(30) NULL,
  to_status VARCHAR(30) NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  details_json LONGTEXT NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_route_execution_event(idempotency_key),
  KEY idx_route_execution_timeline(execution_id,occurred_at,id),
  CONSTRAINT fk_route_execution_timeline FOREIGN KEY(execution_id) REFERENCES monitoramento.route_executions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_route_execution_details CHECK(JSON_VALID(details_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_route_execution_timeline_update BEFORE UPDATE ON monitoramento.route_execution_timeline
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='route execution timeline is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_route_execution_timeline_delete BEFORE DELETE ON monitoramento.route_execution_timeline
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='route execution timeline cannot be deleted'; END$$
DELIMITER ;
