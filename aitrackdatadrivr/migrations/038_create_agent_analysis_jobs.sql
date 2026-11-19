-- UI-5.9: fila durável e idempotente para análise de incidentes.

CREATE TABLE IF NOT EXISTS monitoramento.agent_analysis_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  agent_id BIGINT UNSIGNED NOT NULL,
  incident_id BIGINT UNSIGNED NOT NULL,
  run_id BIGINT UNSIGNED NULL,
  status ENUM('pending','claimed','completed','dead') NOT NULL DEFAULT 'pending',
  priority TINYINT UNSIGNED NOT NULL DEFAULT 50,
  attempt_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  max_attempts SMALLINT UNSIGNED NOT NULL DEFAULT 5,
  idempotency_key VARCHAR(150) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  available_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  claimed_by VARCHAR(100) NULL,
  claimed_at DATETIME(6) NULL,
  lease_expires_at DATETIME(6) NULL,
  last_error_code VARCHAR(100) NULL,
  last_error_message VARCHAR(1000) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_analysis_job_public (public_id),
  UNIQUE KEY uq_agent_analysis_job_idempotency (agent_id,idempotency_key),
  KEY idx_agent_analysis_claim (status,available_at,priority,created_at,id),
  KEY idx_agent_analysis_incident (incident_id,created_at,id),
  CONSTRAINT fk_agent_analysis_agent FOREIGN KEY (agent_id)
    REFERENCES monitoramento.agent_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_analysis_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_analysis_run FOREIGN KEY (run_id)
    REFERENCES monitoramento.agent_runs(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_analysis_priority CHECK (priority BETWEEN 0 AND 100),
  CONSTRAINT chk_agent_analysis_attempts CHECK
    (max_attempts BETWEEN 1 AND 20 AND attempt_count <= max_attempts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
