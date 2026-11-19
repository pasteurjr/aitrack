-- UI-5.14: registrar ações simuladas sem tocar canais externos.

ALTER TABLE monitoramento.agent_autonomy_policies
  ADD COLUMN execution_mode ENUM('simulation','live') NOT NULL DEFAULT 'simulation'
    AFTER autonomy_level;

CREATE TABLE IF NOT EXISTS monitoramento.agent_simulated_actions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  decision_id BIGINT UNSIGNED NOT NULL,
  action_index SMALLINT UNSIGNED NOT NULL,
  action_type VARCHAR(100) NOT NULL,
  priority VARCHAR(20) NOT NULL,
  rationale VARCHAR(500) NOT NULL,
  authorization_json LONGTEXT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_simulated_action (decision_id,action_index),
  CONSTRAINT fk_agent_simulated_action_decision FOREIGN KEY (decision_id)
    REFERENCES monitoramento.agent_run_decisions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_simulated_authorization CHECK (JSON_VALID(authorization_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_simulated_action_immutable_update
BEFORE UPDATE ON monitoramento.agent_simulated_actions
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='simulated agent action is immutable';
END$$
CREATE TRIGGER monitoramento.trg_agent_simulated_action_immutable_delete
BEFORE DELETE ON monitoramento.agent_simulated_actions
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='simulated agent action cannot be deleted';
END$$
DELIMITER ;
