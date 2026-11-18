-- UI-5.1: identidade estável e configuração imutável dos agentes.

CREATE TABLE IF NOT EXISTS monitoramento.agent_definitions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  agent_key VARCHAR(100) NOT NULL,
  display_name VARCHAR(150) NOT NULL,
  monitor_id INT NULL,
  lifecycle_status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_definition_key (agent_key),
  UNIQUE KEY uq_agent_definition_monitor (monitor_id),
  CONSTRAINT fk_agent_definition_monitor FOREIGN KEY (monitor_id)
    REFERENCES monitoramento.monitores(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.agent_config_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  agent_id BIGINT UNSIGNED NOT NULL,
  version_number INT UNSIGNED NOT NULL,
  objective TEXT NOT NULL,
  instructions LONGTEXT NOT NULL,
  provider_code VARCHAR(100) NOT NULL,
  model_code VARCHAR(150) NOT NULL,
  decision_policy_json LONGTEXT NOT NULL,
  limits_json LONGTEXT NOT NULL,
  status ENUM('draft','active','superseded','retired') NOT NULL DEFAULT 'draft',
  active_key VARCHAR(100) NULL,
  content_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  activated_at DATETIME(6) NULL,
  superseded_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_config_version (agent_id,version_number),
  UNIQUE KEY uq_agent_config_active (active_key),
  UNIQUE KEY uq_agent_config_content (agent_id,content_sha256),
  KEY idx_agent_config_status (agent_id,status,version_number),
  CONSTRAINT fk_agent_config_agent FOREIGN KEY (agent_id)
    REFERENCES monitoramento.agent_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_decision_policy CHECK (JSON_VALID(decision_policy_json)),
  CONSTRAINT chk_agent_limits CHECK (JSON_VALID(limits_json)),
  CONSTRAINT chk_agent_active_key CHECK
    ((status='active' AND active_key IS NOT NULL) OR
     (status<>'active' AND active_key IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.agent_config_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  config_version_id BIGINT UNSIGNED NOT NULL,
  event_type ENUM('created','activated','superseded','retired') NOT NULL,
  actor VARCHAR(100) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  snapshot_json LONGTEXT NOT NULL,
  correlation_id VARCHAR(100) NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_config_audit_correlation
    (config_version_id,event_type,correlation_id),
  KEY idx_agent_config_audit (config_version_id,occurred_at,id),
  CONSTRAINT fk_agent_config_audit_version FOREIGN KEY (config_version_id)
    REFERENCES monitoramento.agent_config_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_config_snapshot CHECK (JSON_VALID(snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Monitores existentes viram identidades estáveis, não configurações executáveis.
INSERT IGNORE INTO monitoramento.agent_definitions
  (agent_key,display_name,monitor_id,lifecycle_status)
SELECT CONCAT('monitor-',id),nome,id,IF(ativo,'active','inactive')
  FROM monitoramento.monitores;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_config_immutable_update
BEFORE UPDATE ON monitoramento.agent_config_versions
FOR EACH ROW
BEGIN
  IF NOT (OLD.agent_id <=> NEW.agent_id)
     OR NOT (OLD.version_number <=> NEW.version_number)
     OR NOT (OLD.objective <=> NEW.objective)
     OR NOT (OLD.instructions <=> NEW.instructions)
     OR NOT (OLD.provider_code <=> NEW.provider_code)
     OR NOT (OLD.model_code <=> NEW.model_code)
     OR NOT (OLD.decision_policy_json <=> NEW.decision_policy_json)
     OR NOT (OLD.limits_json <=> NEW.limits_json)
     OR NOT (OLD.content_sha256 <=> NEW.content_sha256)
     OR NOT (OLD.created_by <=> NEW.created_by)
     OR NOT (OLD.change_reason <=> NEW.change_reason)
     OR NOT (OLD.created_at <=> NEW.created_at) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent config content is immutable';
  END IF;
END$$

CREATE TRIGGER monitoramento.trg_agent_config_immutable_delete
BEFORE DELETE ON monitoramento.agent_config_versions
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent config versions cannot be deleted';
END$$
DELIMITER ;
