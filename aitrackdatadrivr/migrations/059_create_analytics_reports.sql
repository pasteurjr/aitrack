-- UI-7.7: definições versionadas e execuções rastreáveis de relatório.
CREATE TABLE IF NOT EXISTS monitoramento.report_definitions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_key VARCHAR(100) NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  metrics_json LONGTEXT NOT NULL,
  formula_version VARCHAR(50) NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_report_definition(report_key,version_no),
  CONSTRAINT chk_report_metrics CHECK(JSON_VALID(metrics_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.report_definitions
  (report_key,version_no,title,metrics_json,formula_version,created_by)
VALUES
  ('behavior_summary',1,'Resumo comportamental por fonte',
   '["event_count","distance_km","driving_hours","events_per_100_km","events_per_driving_hour","coverage"]',
   'exposure-v1','migration-059');

CREATE TABLE IF NOT EXISTS monitoramento.report_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  definition_id BIGINT UNSIGNED NOT NULL,
  request_hash CHAR(64) NOT NULL,
  mode ENUM('tracker','dirijabem','unified') NOT NULL,
  filters_json LONGTEXT NOT NULL,
  sources_json LONGTEXT NOT NULL,
  result_json LONGTEXT NOT NULL,
  status ENUM('completed','failed') NOT NULL,
  row_count INT UNSIGNED NOT NULL DEFAULT 0,
  generated_by VARCHAR(100) NOT NULL,
  generated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_report_run_public(public_id),
  UNIQUE KEY uq_report_request_hash(request_hash),
  KEY idx_report_run_time(generated_at,id),
  CONSTRAINT fk_report_run_definition FOREIGN KEY(definition_id)
    REFERENCES monitoramento.report_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_report_filters CHECK(JSON_VALID(filters_json)),
  CONSTRAINT chk_report_sources CHECK(JSON_VALID(sources_json)),
  CONSTRAINT chk_report_result CHECK(JSON_VALID(result_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_report_run_update BEFORE UPDATE ON monitoramento.report_runs
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='completed report run is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_report_run_delete BEFORE DELETE ON monitoramento.report_runs
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='report run cannot be deleted'; END$$
DELIMITER ;
