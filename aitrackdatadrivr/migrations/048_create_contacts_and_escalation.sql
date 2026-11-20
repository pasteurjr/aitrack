-- UI-6.7: contatos consentidos e política versionada de escalonamento.
CREATE TABLE IF NOT EXISTS monitoramento.contact_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  owner_ref VARCHAR(100) NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  role ENUM('owner','manager','operations_center') NOT NULL,
  display_name VARCHAR(150) NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_contact_profile_public(public_id),
  KEY idx_contact_profile_resolve(owner_ref,vehicle_id,role,active),
  CONSTRAINT fk_contact_profile_vehicle FOREIGN KEY(vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.contact_channels (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  contact_id BIGINT UNSIGNED NOT NULL,
  channel ENUM('sms','whatsapp','voice','email','internal') NOT NULL,
  destination_ref VARCHAR(200) NOT NULL,
  destination_hash CHAR(64) NOT NULL,
  priority SMALLINT UNSIGNED NOT NULL DEFAULT 100,
  verified_at DATETIME(6) NULL,
  consent_status ENUM('pending','granted','revoked','expired') NOT NULL,
  consent_scope VARCHAR(100) NOT NULL,
  consent_source VARCHAR(100) NOT NULL,
  consent_granted_at DATETIME(6) NULL,
  consent_revoked_at DATETIME(6) NULL,
  consent_expires_at DATETIME(6) NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_contact_channel_hash(contact_id,channel,destination_hash),
  KEY idx_contact_channel_eligible(channel,consent_status,active,priority),
  CONSTRAINT fk_contact_channel_contact FOREIGN KEY(contact_id)
    REFERENCES monitoramento.contact_profiles(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.escalation_policy_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_key VARCHAR(100) NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  status ENUM('draft','active','superseded') NOT NULL DEFAULT 'draft',
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  activated_by VARCHAR(100) NULL,
  activated_at DATETIME(6) NULL,
  active_policy_key VARCHAR(100) AS (CASE WHEN status='active' THEN policy_key ELSE NULL END) PERSISTENT,
  PRIMARY KEY(id), UNIQUE KEY uq_escalation_policy_version(policy_key,version_no),
  UNIQUE KEY uq_escalation_policy_active(active_policy_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.escalation_policy_steps (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_version_id BIGINT UNSIGNED NOT NULL,
  step_order SMALLINT UNSIGNED NOT NULL,
  contact_role ENUM('owner','manager','operations_center') NOT NULL,
  channel ENUM('sms','whatsapp','voice','email','internal') NOT NULL,
  wait_seconds INT UNSIGNED NOT NULL DEFAULT 0,
  min_severity ENUM('low','medium','high','critical') NOT NULL DEFAULT 'low',
  PRIMARY KEY(id), UNIQUE KEY uq_escalation_step(policy_version_id,step_order),
  CONSTRAINT fk_escalation_step_policy FOREIGN KEY(policy_version_id)
    REFERENCES monitoramento.escalation_policy_versions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.contact_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  contact_id BIGINT UNSIGNED NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  snapshot_json LONGTEXT NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), KEY idx_contact_audit(contact_id,occurred_at,id),
  CONSTRAINT fk_contact_audit_contact FOREIGN KEY(contact_id)
    REFERENCES monitoramento.contact_profiles(id) ON DELETE RESTRICT,
  CONSTRAINT chk_contact_audit_snapshot CHECK(JSON_VALID(snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_contact_audit_update BEFORE UPDATE ON monitoramento.contact_audit
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='contact audit is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_contact_audit_delete BEFORE DELETE ON monitoramento.contact_audit
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='contact audit cannot be deleted'; END$$
DELIMITER ;
