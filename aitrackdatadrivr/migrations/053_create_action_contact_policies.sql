-- UI-6.13: limites versionados antes de qualquer contato externo.
CREATE TABLE IF NOT EXISTS monitoramento.action_contact_policy_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_key VARCHAR(100) NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  channel ENUM('all','message','voice') NOT NULL DEFAULT 'all',
  timezone_name VARCHAR(100) NOT NULL,
  quiet_start TIME NOT NULL,
  quiet_end TIME NOT NULL,
  max_attempts_per_incident SMALLINT UNSIGNED NOT NULL,
  max_contacts_per_target_day SMALLINT UNSIGNED NOT NULL,
  max_cost_cents_per_target_day INT UNSIGNED NOT NULL,
  cooldown_seconds INT UNSIGNED NOT NULL,
  max_consecutive_no_progress SMALLINT UNSIGNED NOT NULL,
  status ENUM('draft','active','superseded') NOT NULL DEFAULT 'draft',
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  active_policy_key VARCHAR(120) AS
    (CASE WHEN status='active' THEN CONCAT(policy_key,':',channel) ELSE NULL END) PERSISTENT,
  PRIMARY KEY(id), UNIQUE KEY uq_contact_policy_version(policy_key,version_no,channel),
  UNIQUE KEY uq_contact_policy_active(active_policy_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.action_policy_decisions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  action_id BIGINT UNSIGNED NOT NULL,
  policy_version_id BIGINT UNSIGNED NOT NULL,
  evaluation_key VARCHAR(180) NOT NULL,
  allowed BOOLEAN NOT NULL,
  denial_codes_json LONGTEXT NOT NULL,
  context_snapshot_json LONGTEXT NOT NULL,
  target_hash CHAR(64) NOT NULL,
  estimated_cost_cents INT UNSIGNED NOT NULL,
  evaluated_local_at DATETIME(6) NOT NULL,
  next_allowed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_action_policy_evaluation(evaluation_key),
  KEY idx_action_policy_daily(target_hash,created_at,allowed),
  CONSTRAINT fk_action_policy_decision_action FOREIGN KEY(action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT fk_action_policy_decision_version FOREIGN KEY(policy_version_id)
    REFERENCES monitoramento.action_contact_policy_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_action_policy_denials CHECK(JSON_VALID(denial_codes_json)),
  CONSTRAINT chk_action_policy_context CHECK(JSON_VALID(context_snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO monitoramento.action_contact_policy_versions
  (policy_key,version_no,channel,timezone_name,quiet_start,quiet_end,
   max_attempts_per_incident,max_contacts_per_target_day,
   max_cost_cents_per_target_day,cooldown_seconds,max_consecutive_no_progress,
   status,created_by)
SELECT 'external-contact-default',1,'all','America/Sao_Paulo','20:00:00','08:00:00',
       3,4,1000,900,2,'active','migration-053'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM monitoramento.action_contact_policy_versions
   WHERE policy_key='external-contact-default' AND version_no=1 AND channel='all'
);

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_policy_decision_update BEFORE UPDATE ON monitoramento.action_policy_decisions
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='action policy decisions are immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_policy_decision_delete BEFORE DELETE ON monitoramento.action_policy_decisions
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='action policy decisions cannot be deleted'; END$$
DELIMITER ;
