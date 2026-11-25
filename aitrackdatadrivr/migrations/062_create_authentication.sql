-- UI-8.1: identidade humana e sessões opacas no servidor.
CREATE TABLE IF NOT EXISTS monitoramento.tenants (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  slug VARCHAR(100) NOT NULL,
  name VARCHAR(200) NOT NULL,
  status ENUM('active','suspended') NOT NULL DEFAULT 'active',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_tenant_public(public_id), UNIQUE KEY uq_tenant_slug(slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  email_normalized VARCHAR(254) NOT NULL,
  display_name VARCHAR(150) NOT NULL,
  password_hash VARCHAR(100) NOT NULL,
  status ENUM('active','disabled') NOT NULL DEFAULT 'active',
  failed_attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  locked_until DATETIME(6) NULL,
  password_changed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  last_login_at DATETIME(6) NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_auth_user_public(public_id),
  UNIQUE KEY uq_auth_user_email(email_normalized)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_memberships (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  tenant_id BIGINT UNSIGNED NOT NULL,
  status ENUM('active','disabled') NOT NULL DEFAULT 'active',
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_auth_membership(user_id,tenant_id),
  KEY idx_auth_membership_tenant(tenant_id,status,user_id),
  CONSTRAINT fk_auth_membership_user FOREIGN KEY(user_id) REFERENCES monitoramento.auth_users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_auth_membership_tenant FOREIGN KEY(tenant_id) REFERENCES monitoramento.tenants(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  token_sha256 CHAR(64) NOT NULL,
  csrf_sha256 CHAR(64) NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  tenant_id BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  last_seen_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  idle_expires_at DATETIME(6) NOT NULL,
  absolute_expires_at DATETIME(6) NOT NULL,
  revoked_at DATETIME(6) NULL,
  revoke_reason VARCHAR(100) NULL,
  PRIMARY KEY(id), UNIQUE KEY uq_auth_session_public(public_id),
  UNIQUE KEY uq_auth_session_token(token_sha256),
  KEY idx_auth_session_user(user_id,revoked_at,absolute_expires_at),
  KEY idx_auth_session_expiry(idle_expires_at,absolute_expires_at),
  CONSTRAINT fk_auth_session_user FOREIGN KEY(user_id) REFERENCES monitoramento.auth_users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_auth_session_tenant FOREIGN KEY(tenant_id) REFERENCES monitoramento.tenants(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_password_reset_tokens (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  token_sha256 CHAR(64) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  consumed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_auth_reset_token(token_sha256),
  KEY idx_auth_reset_user(user_id,expires_at),
  CONSTRAINT fk_auth_reset_user FOREIGN KEY(user_id) REFERENCES monitoramento.auth_users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_security_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NULL,
  tenant_id BIGINT UNSIGNED NULL,
  event_type VARCHAR(50) NOT NULL,
  request_id VARCHAR(100) NULL,
  source_ip_sha256 CHAR(64) NULL,
  details_json LONGTEXT NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), KEY idx_auth_event_time(occurred_at,id),
  KEY idx_auth_event_user(user_id,occurred_at,id),
  CONSTRAINT fk_auth_event_user FOREIGN KEY(user_id) REFERENCES monitoramento.auth_users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_auth_event_tenant FOREIGN KEY(tenant_id) REFERENCES monitoramento.tenants(id) ON DELETE RESTRICT,
  CONSTRAINT chk_auth_event_details CHECK(JSON_VALID(details_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_auth_event_update BEFORE UPDATE ON monitoramento.auth_security_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='auth security event is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_auth_event_delete BEFORE DELETE ON monitoramento.auth_security_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='auth security event cannot be deleted'; END$$
DELIMITER ;
