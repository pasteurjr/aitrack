-- UI-5.7: allowlist imutável de ferramentas por versão do agente.

CREATE TABLE IF NOT EXISTS monitoramento.agent_tool_policies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  config_version_id BIGINT UNSIGNED NOT NULL,
  tool_name VARCHAR(100) NOT NULL,
  constraints_json LONGTEXT NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_tool_policy (config_version_id,tool_name),
  KEY idx_agent_tool_policy_version (config_version_id,id),
  CONSTRAINT fk_agent_tool_policy_version FOREIGN KEY (config_version_id)
    REFERENCES monitoramento.agent_config_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_tool_policy_constraints CHECK (JSON_VALID(constraints_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_tool_policy_immutable_update
BEFORE UPDATE ON monitoramento.agent_tool_policies
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent tool policy is immutable';
END$$

CREATE TRIGGER monitoramento.trg_agent_tool_policy_immutable_delete
BEFORE DELETE ON monitoramento.agent_tool_policies
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent tool policies cannot be deleted';
END$$
DELIMITER ;
