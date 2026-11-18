-- UI-4.11: autorização reforçada e fail-closed para comandos críticos.

CREATE TABLE IF NOT EXISTS monitoramento.command_principals (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id VARCHAR(100) NOT NULL,
  display_name VARCHAR(150) NOT NULL,
  role ENUM('operator','supervisor','admin') NOT NULL,
  token_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  revoked_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_command_principal_public (public_id),
  UNIQUE KEY uq_command_principal_token (token_sha256),
  KEY idx_command_principal_active_role (active,role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.command_authorization_policies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  capability_code VARCHAR(100) NOT NULL,
  version_number INT UNSIGNED NOT NULL,
  status ENUM('draft','active','superseded') NOT NULL DEFAULT 'draft',
  critical BOOLEAN NOT NULL DEFAULT TRUE,
  requester_role ENUM('operator','supervisor','admin') NOT NULL,
  approver_role ENUM('operator','supervisor','admin') NOT NULL,
  required_approvals TINYINT UNSIGNED NOT NULL DEFAULT 1,
  confirmation_text VARCHAR(100) NOT NULL,
  max_timeout_seconds SMALLINT UNSIGNED NOT NULL DEFAULT 60,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_command_auth_policy_version (capability_code,version_number),
  KEY idx_command_auth_policy_active (capability_code,status,version_number),
  CONSTRAINT chk_command_auth_approvals CHECK (required_approvals BETWEEN 0 AND 2),
  CONSTRAINT chk_command_auth_timeout CHECK (max_timeout_seconds BETWEEN 5 AND 300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE monitoramento.device_commands
  ADD COLUMN authorization_policy_id BIGINT UNSIGNED NULL AFTER capability_code,
  ADD COLUMN requester_principal_id BIGINT UNSIGNED NULL AFTER requested_by_name,
  ADD COLUMN approval_status ENUM('not_required','pending','approved','rejected')
    NOT NULL DEFAULT 'pending' AFTER reason,
  ADD COLUMN authorization_snapshot_json LONGTEXT NULL AFTER approval_status,
  ADD CONSTRAINT fk_device_command_auth_policy FOREIGN KEY (authorization_policy_id)
    REFERENCES monitoramento.command_authorization_policies(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_device_command_requester FOREIGN KEY (requester_principal_id)
    REFERENCES monitoramento.command_principals(id) ON DELETE RESTRICT,
  ADD CONSTRAINT chk_device_command_auth_snapshot CHECK
    (authorization_snapshot_json IS NULL OR JSON_VALID(authorization_snapshot_json));

CREATE TABLE IF NOT EXISTS monitoramento.device_command_approvals (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  command_id BIGINT UNSIGNED NOT NULL,
  principal_id BIGINT UNSIGNED NOT NULL,
  decision ENUM('approved','rejected') NOT NULL,
  reason VARCHAR(500) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  decided_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_command_approval_principal (command_id,principal_id),
  UNIQUE KEY uq_command_approval_correlation (command_id,correlation_id),
  KEY idx_command_approval_audit (command_id,decided_at,id),
  CONSTRAINT fk_command_approval_command FOREIGN KEY (command_id)
    REFERENCES monitoramento.device_commands(id) ON DELETE RESTRICT,
  CONSTRAINT fk_command_approval_principal FOREIGN KEY (principal_id)
    REFERENCES monitoramento.command_principals(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Políticas não habilitam o hardware: apenas especificam o que será exigido se a
-- capacidade vier a ser comprovada e o ambiente estiver confirmado em produção.
INSERT IGNORE INTO monitoramento.command_authorization_policies
  (capability_code,version_number,status,critical,requester_role,approver_role,
   required_approvals,confirmation_text,max_timeout_seconds,created_by,change_reason)
VALUES
  ('remote_immobilization',1,'active',TRUE,'operator','supervisor',1,
   'CONFIRMAR BLOQUEIO',60,'codex-ui-4.11','Política inicial fail-closed'),
  ('buzzer_activation',1,'active',TRUE,'operator','supervisor',1,
   'CONFIRMAR SIRENE',60,'codex-ui-4.11','Política inicial fail-closed');
