-- UI-4.3: política operacional versionada, separada da capacidade física.

CREATE TABLE IF NOT EXISTS monitoramento.detector_policies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_key VARCHAR(100) NOT NULL,
  version_number INT UNSIGNED NOT NULL,
  detector_type VARCHAR(100) NOT NULL,
  capability_code VARCHAR(100) NULL,
  scope_type ENUM('global','source','monitor','vehicle') NOT NULL,
  scope_ref VARCHAR(100) NOT NULL DEFAULT '*',
  parameters_json LONGTEXT NOT NULL,
  status ENUM('draft','active','superseded','retired') NOT NULL DEFAULT 'draft',
  active_key VARCHAR(255) NULL,
  created_by VARCHAR(100) NOT NULL,
  change_reason VARCHAR(500) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  activated_at DATETIME(6) NULL,
  superseded_at DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_detector_policy_version (policy_key, scope_type, scope_ref, version_number),
  UNIQUE KEY uq_detector_policy_active (active_key),
  KEY idx_detector_policy_lookup (detector_type, scope_type, scope_ref, status),
  CONSTRAINT chk_detector_policy_parameters CHECK (JSON_VALID(parameters_json)),
  CONSTRAINT chk_detector_policy_active_key CHECK
    ((status = 'active' AND active_key IS NOT NULL) OR
     (status <> 'active' AND active_key IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.detector_policy_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  policy_id BIGINT UNSIGNED NOT NULL,
  event_type ENUM('created','activated','superseded','retired') NOT NULL,
  actor VARCHAR(100) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  snapshot_json LONGTEXT NOT NULL,
  correlation_id VARCHAR(100) NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_detector_policy_audit (policy_id, occurred_at, id),
  CONSTRAINT fk_detector_policy_audit_policy FOREIGN KEY (policy_id)
    REFERENCES monitoramento.detector_policies(id) ON DELETE RESTRICT,
  CONSTRAINT chk_detector_policy_snapshot CHECK (JSON_VALID(snapshot_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
