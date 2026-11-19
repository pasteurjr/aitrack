-- UI-6.1: contrato comum e durável para toda ação operacional.

CREATE TABLE IF NOT EXISTS monitoramento.action_queue (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  incident_id BIGINT UNSIGNED NOT NULL,
  agent_run_id BIGINT UNSIGNED NULL,
  decision_id BIGINT UNSIGNED NULL,
  action_index SMALLINT UNSIGNED NULL,
  action_type ENUM('internal_notification','send_message','call_owner','notify_authorities','vehicle_command') NOT NULL,
  target_type ENUM('operator','contact','authority','vehicle') NOT NULL,
  target_ref VARCHAR(150) NOT NULL,
  payload_json LONGTEXT NOT NULL,
  policy_snapshot_json LONGTEXT NOT NULL,
  priority ENUM('low','normal','high','urgent') NOT NULL DEFAULT 'normal',
  status ENUM('pending','awaiting_approval','approved','claimed','sent','delivered','responded','failed','dead','cancelled','simulated') NOT NULL DEFAULT 'pending',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  attempt_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  max_attempts SMALLINT UNSIGNED NOT NULL DEFAULT 5,
  idempotency_key VARCHAR(150) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  causation_id VARCHAR(100) NULL,
  available_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  claimed_by VARCHAR(100) NULL,
  lease_expires_at DATETIME(6) NULL,
  last_error_code VARCHAR(100) NULL,
  last_error_message VARCHAR(1000) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_action_queue_public (public_id),
  UNIQUE KEY uq_action_queue_idempotency (idempotency_key),
  UNIQUE KEY uq_action_queue_decision_index (decision_id,action_index),
  KEY idx_action_queue_claim (status,available_at,priority,created_at,id),
  KEY idx_action_queue_incident (incident_id,created_at,id),
  KEY idx_action_queue_correlation (correlation_id,id),
  CONSTRAINT fk_action_queue_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT,
  CONSTRAINT fk_action_queue_run FOREIGN KEY (agent_run_id)
    REFERENCES monitoramento.agent_runs(id) ON DELETE RESTRICT,
  CONSTRAINT fk_action_queue_decision FOREIGN KEY (decision_id)
    REFERENCES monitoramento.agent_run_decisions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_action_queue_payload CHECK (JSON_VALID(payload_json)),
  CONSTRAINT chk_action_queue_policy CHECK (JSON_VALID(policy_snapshot_json)),
  CONSTRAINT chk_action_queue_attempts CHECK
    (max_attempts BETWEEN 1 AND 20 AND attempt_count <= max_attempts),
  CONSTRAINT chk_action_queue_decision_pair CHECK
    ((decision_id IS NULL AND action_index IS NULL) OR
     (decision_id IS NOT NULL AND action_index IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.action_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  action_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  from_status VARCHAR(30) NULL,
  to_status VARCHAR(30) NOT NULL,
  actor_type ENUM('system','agent','human','provider') NOT NULL,
  actor_id VARCHAR(100) NULL,
  details_json LONGTEXT NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_action_event_idempotency (idempotency_key),
  KEY idx_action_event_timeline (action_id,occurred_at,id),
  CONSTRAINT fk_action_event_action FOREIGN KEY (action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT chk_action_event_details CHECK (JSON_VALID(details_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_action_event_immutable_update
BEFORE UPDATE ON monitoramento.action_events
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='action events are immutable';
END$$
CREATE TRIGGER monitoramento.trg_action_event_immutable_delete
BEFORE DELETE ON monitoramento.action_events
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='action events cannot be deleted';
END$$
DELIMITER ;
