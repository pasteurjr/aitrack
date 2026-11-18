-- UI-5.2: ledger rastreável de execuções e decisões dos agentes.

CREATE TABLE IF NOT EXISTS monitoramento.agent_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  agent_id BIGINT UNSIGNED NOT NULL,
  config_version_id BIGINT UNSIGNED NOT NULL,
  incident_id BIGINT UNSIGNED NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  trigger_type ENUM('scheduled','event','manual','retry') NOT NULL,
  status ENUM('queued','running','succeeded','failed','timed_out','cancelled') NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  attempt_number SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  idempotency_key VARCHAR(150) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  causation_id VARCHAR(100) NULL,
  provider_code VARCHAR(100) NOT NULL,
  model_code VARCHAR(150) NOT NULL,
  input_json LONGTEXT NOT NULL,
  context_json LONGTEXT NOT NULL,
  output_json LONGTEXT NULL,
  input_tokens INT UNSIGNED NULL,
  output_tokens INT UNSIGNED NULL,
  cost_usd DECIMAL(12,6) NULL,
  latency_ms INT UNSIGNED NULL,
  error_code VARCHAR(100) NULL,
  error_message VARCHAR(1000) NULL,
  queued_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  started_at DATETIME(6) NULL,
  completed_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_run_public (public_id),
  UNIQUE KEY uq_agent_run_idempotency (agent_id,idempotency_key),
  KEY idx_agent_run_status (status,queued_at,id),
  KEY idx_agent_run_agent (agent_id,queued_at,id),
  KEY idx_agent_run_incident (incident_id,queued_at,id),
  KEY idx_agent_run_correlation (correlation_id,id),
  CONSTRAINT fk_agent_run_agent FOREIGN KEY (agent_id)
    REFERENCES monitoramento.agent_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_run_config FOREIGN KEY (config_version_id)
    REFERENCES monitoramento.agent_config_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_run_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_run_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_run_input CHECK (JSON_VALID(input_json)),
  CONSTRAINT chk_agent_run_context CHECK (JSON_VALID(context_json)),
  CONSTRAINT chk_agent_run_output CHECK (output_json IS NULL OR JSON_VALID(output_json)),
  CONSTRAINT chk_agent_run_attempt CHECK (attempt_number BETWEEN 1 AND 20),
  CONSTRAINT chk_agent_run_cost CHECK (cost_usd IS NULL OR cost_usd >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.agent_run_decisions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id BIGINT UNSIGNED NOT NULL,
  format_version VARCHAR(50) NOT NULL,
  decision_json LONGTEXT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_run_decision (run_id),
  CONSTRAINT fk_agent_run_decision_run FOREIGN KEY (run_id)
    REFERENCES monitoramento.agent_runs(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_run_decision_json CHECK (JSON_VALID(decision_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_run_identity_immutable
BEFORE UPDATE ON monitoramento.agent_runs
FOR EACH ROW
BEGIN
  IF NOT (OLD.public_id <=> NEW.public_id)
     OR NOT (OLD.agent_id <=> NEW.agent_id)
     OR NOT (OLD.config_version_id <=> NEW.config_version_id)
     OR NOT (OLD.incident_id <=> NEW.incident_id)
     OR NOT (OLD.vehicle_id <=> NEW.vehicle_id)
     OR NOT (OLD.trigger_type <=> NEW.trigger_type)
     OR NOT (OLD.attempt_number <=> NEW.attempt_number)
     OR NOT (OLD.idempotency_key <=> NEW.idempotency_key)
     OR NOT (OLD.correlation_id <=> NEW.correlation_id)
     OR NOT (OLD.causation_id <=> NEW.causation_id)
     OR NOT (OLD.provider_code <=> NEW.provider_code)
     OR NOT (OLD.model_code <=> NEW.model_code)
     OR NOT (OLD.input_json <=> NEW.input_json)
     OR NOT (OLD.context_json <=> NEW.context_json)
     OR OLD.status IN ('succeeded','failed','timed_out','cancelled') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent run identity/final state is immutable';
  END IF;
END$$

CREATE TRIGGER monitoramento.trg_agent_decision_immutable_update
BEFORE UPDATE ON monitoramento.agent_run_decisions
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent decision is immutable';
END$$

CREATE TRIGGER monitoramento.trg_agent_decision_immutable_delete
BEFORE DELETE ON monitoramento.agent_run_decisions
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent decisions cannot be deleted';
END$$
DELIMITER ;
