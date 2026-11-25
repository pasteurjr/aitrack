-- UI-7.9: exportações internas auditáveis; entrega externa bloqueada até RBAC.
CREATE TABLE IF NOT EXISTS monitoramento.report_export_schedules (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  report_definition_id BIGINT UNSIGNED NOT NULL,
  mode ENUM('tracker','dirijabem','unified') NOT NULL,
  format ENUM('csv','json') NOT NULL,
  filters_json LONGTEXT NOT NULL,
  timezone_name VARCHAR(100) NOT NULL,
  cadence ENUM('daily','weekly') NOT NULL,
  local_time TIME NOT NULL,
  weekday TINYINT UNSIGNED NULL,
  destination_type ENUM('internal_download') NOT NULL DEFAULT 'internal_download',
  destination_ref VARCHAR(150) NOT NULL,
  status ENUM('blocked_auth','active','paused') NOT NULL DEFAULT 'blocked_auth',
  next_run_at DATETIME(6) NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_export_schedule_public(public_id),
  KEY idx_export_schedule_due(status,next_run_at,id),
  CONSTRAINT fk_export_schedule_definition FOREIGN KEY(report_definition_id)
    REFERENCES monitoramento.report_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_export_schedule_filters CHECK(JSON_VALID(filters_json)),
  CONSTRAINT chk_export_schedule_weekday CHECK(weekday IS NULL OR weekday BETWEEN 0 AND 6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.report_export_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  schedule_id BIGINT UNSIGNED NULL,
  report_run_id BIGINT UNSIGNED NOT NULL,
  format ENUM('csv','json') NOT NULL,
  status ENUM('completed','failed') NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  permission_snapshot_json LONGTEXT NOT NULL,
  artifact_ref VARCHAR(200) NOT NULL,
  artifact_sha256 CHAR(64) NOT NULL,
  artifact_size_bytes BIGINT UNSIGNED NOT NULL,
  row_count INT UNSIGNED NOT NULL,
  error_code VARCHAR(100) NULL,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_export_job_public(public_id),
  UNIQUE KEY uq_export_job_idempotency(idempotency_key),
  KEY idx_export_job_schedule(schedule_id,created_at,id),
  CONSTRAINT fk_export_job_schedule FOREIGN KEY(schedule_id)
    REFERENCES monitoramento.report_export_schedules(id) ON DELETE RESTRICT,
  CONSTRAINT fk_export_job_report FOREIGN KEY(report_run_id)
    REFERENCES monitoramento.report_runs(id) ON DELETE RESTRICT,
  CONSTRAINT chk_export_permission CHECK(JSON_VALID(permission_snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.report_export_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  details_json LONGTEXT NOT NULL,
  idempotency_key VARCHAR(180) NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_export_event_idempotency(idempotency_key),
  KEY idx_export_event_job(job_id,occurred_at,id),
  CONSTRAINT fk_export_event_job FOREIGN KEY(job_id)
    REFERENCES monitoramento.report_export_jobs(id) ON DELETE RESTRICT,
  CONSTRAINT chk_export_event_details CHECK(JSON_VALID(details_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_export_job_update BEFORE UPDATE ON monitoramento.report_export_jobs
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='export job is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_export_job_delete BEFORE DELETE ON monitoramento.report_export_jobs
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='export job cannot be deleted'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_export_event_update BEFORE UPDATE ON monitoramento.report_export_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='export event is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_export_event_delete BEFORE DELETE ON monitoramento.report_export_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='export event cannot be deleted'; END$$
DELIMITER ;
