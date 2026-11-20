-- UI-6.8: aprovação humana versionada, independente e com expiração.
CREATE TABLE IF NOT EXISTS monitoramento.action_approvals (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  action_id BIGINT UNSIGNED NOT NULL,
  action_version_requested INT UNSIGNED NOT NULL,
  status ENUM('pending','approved','rejected','expired') NOT NULL DEFAULT 'pending',
  required_role ENUM('supervisor','security_manager','administrator') NOT NULL,
  requested_by_type ENUM('agent','human','system') NOT NULL,
  requested_by VARCHAR(100) NOT NULL,
  request_reason VARCHAR(1000) NOT NULL,
  policy_snapshot_json LONGTEXT NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  decided_by VARCHAR(100) NULL,
  decided_role VARCHAR(50) NULL,
  decision_reason VARCHAR(1000) NULL,
  decision_idempotency_key VARCHAR(150) NULL,
  decided_at DATETIME(6) NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_action_approval_public(public_id),
  UNIQUE KEY uq_action_approval_action(action_id),
  UNIQUE KEY uq_action_approval_decision_key(decision_idempotency_key),
  KEY idx_action_approval_pending(status,expires_at,id),
  CONSTRAINT fk_action_approval_action FOREIGN KEY(action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT chk_action_approval_policy CHECK(JSON_VALID(policy_snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_approval_guard
BEFORE UPDATE ON monitoramento.action_approvals FOR EACH ROW BEGIN
  IF NOT (OLD.public_id <=> NEW.public_id) OR NOT (OLD.action_id <=> NEW.action_id)
     OR NOT (OLD.action_version_requested <=> NEW.action_version_requested)
     OR NOT (OLD.required_role <=> NEW.required_role)
     OR NOT (OLD.requested_by <=> NEW.requested_by)
     OR NOT (OLD.request_reason <=> NEW.request_reason)
     OR OLD.status <> 'pending' OR NEW.status NOT IN ('approved','rejected','expired') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='approval identity or terminal decision is immutable';
  END IF;
END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_approval_delete
BEFORE DELETE ON monitoramento.action_approvals FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='approvals cannot be deleted';
END$$
DELIMITER ;
