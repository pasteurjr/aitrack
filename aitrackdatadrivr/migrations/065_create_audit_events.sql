-- UI-8.4: trilha transversal consultável, append-only e isolada por tenant.
CREATE TABLE IF NOT EXISTS monitoramento.audit_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  tenant_id BIGINT UNSIGNED NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  actor_type ENUM('human','agent','system','integration') NOT NULL,
  actor_user_id BIGINT UNSIGNED NULL,
  actor_public_id VARCHAR(100) NULL,
  actor_display VARCHAR(150) NULL,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(100) NOT NULL,
  resource_public_id VARCHAR(150) NULL,
  before_json LONGTEXT NULL,
  after_json LONGTEXT NULL,
  reason VARCHAR(500) NULL,
  correlation_id VARCHAR(100) NULL,
  causation_id VARCHAR(100) NULL,
  request_id VARCHAR(100) NULL,
  source_ip_sha256 CHAR(64) NULL,
  user_agent VARCHAR(300) NULL,
  metadata_json LONGTEXT NOT NULL,
  PRIMARY KEY(id),
  UNIQUE KEY uq_audit_public(public_id),
  KEY idx_audit_tenant_time(tenant_id, occurred_at, id),
  KEY idx_audit_resource(tenant_id, resource_type, resource_public_id, occurred_at, id),
  KEY idx_audit_actor(tenant_id, actor_public_id, occurred_at, id),
  KEY idx_audit_correlation(tenant_id, correlation_id, id),
  CONSTRAINT fk_audit_tenant FOREIGN KEY(tenant_id)
    REFERENCES monitoramento.tenants(id) ON DELETE RESTRICT,
  CONSTRAINT fk_audit_user FOREIGN KEY(actor_user_id)
    REFERENCES monitoramento.auth_users(id) ON DELETE SET NULL,
  CONSTRAINT chk_audit_before CHECK(before_json IS NULL OR JSON_VALID(before_json)),
  CONSTRAINT chk_audit_after CHECK(after_json IS NULL OR JSON_VALID(after_json)),
  CONSTRAINT chk_audit_metadata CHECK(JSON_VALID(metadata_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_audit_events_update
BEFORE UPDATE ON monitoramento.audit_events FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit event is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_audit_events_delete
BEFORE DELETE ON monitoramento.audit_events FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit event cannot be deleted'; END$$
DELIMITER ;
