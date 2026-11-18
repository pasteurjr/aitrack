-- UI-5.8: autonomia versionada e autorização persistida de cada decisão.

CREATE TABLE IF NOT EXISTS monitoramento.agent_autonomy_policies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  config_version_id BIGINT UNSIGNED NOT NULL,
  autonomy_level ENUM('observe','recommend','approval','execute') NOT NULL,
  max_autonomous_risk ENUM('none','low','medium') NOT NULL DEFAULT 'none',
  allowed_autonomous_actions_json LONGTEXT NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_autonomy_policy_version (config_version_id),
  CONSTRAINT fk_agent_autonomy_policy_version FOREIGN KEY (config_version_id)
    REFERENCES monitoramento.agent_config_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_autonomy_actions CHECK
    (JSON_VALID(allowed_autonomous_actions_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE monitoramento.agent_run_decisions
  ADD COLUMN autonomy_policy_id BIGINT UNSIGNED NULL AFTER validated_at,
  ADD COLUMN autonomy_level ENUM('observe','recommend','approval','execute') NULL
    AFTER autonomy_policy_id,
  ADD COLUMN authorization_json LONGTEXT NULL AFTER autonomy_level,
  ADD KEY idx_agent_decision_autonomy (autonomy_policy_id),
  ADD CONSTRAINT fk_agent_decision_autonomy FOREIGN KEY (autonomy_policy_id)
    REFERENCES monitoramento.agent_autonomy_policies(id) ON DELETE RESTRICT,
  ADD CONSTRAINT chk_agent_decision_authorization CHECK
    (authorization_json IS NULL OR JSON_VALID(authorization_json));

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_autonomy_draft_insert
BEFORE INSERT ON monitoramento.agent_autonomy_policies
FOR EACH ROW
BEGIN
  DECLARE config_status VARCHAR(20);
  SELECT status INTO config_status
    FROM monitoramento.agent_config_versions WHERE id=NEW.config_version_id;
  IF config_status <> 'draft' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='autonomy policy requires draft config';
  END IF;
END$$

CREATE TRIGGER monitoramento.trg_agent_autonomy_immutable_update
BEFORE UPDATE ON monitoramento.agent_autonomy_policies
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent autonomy policy is immutable';
END$$

CREATE TRIGGER monitoramento.trg_agent_autonomy_immutable_delete
BEFORE DELETE ON monitoramento.agent_autonomy_policies
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent autonomy policies cannot be deleted';
END$$
DELIMITER ;
