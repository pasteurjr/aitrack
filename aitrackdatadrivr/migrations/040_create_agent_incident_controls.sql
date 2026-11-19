-- UI-5.13: pausa/takeover humano versionados por incidente.

CREATE TABLE IF NOT EXISTS monitoramento.agent_incident_controls (
  incident_id BIGINT UNSIGNED NOT NULL,
  agent_id BIGINT UNSIGNED NULL,
  control_state ENUM('active','paused','human_owned') NOT NULL DEFAULT 'active',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  human_owner_id VARCHAR(100) NULL,
  reason VARCHAR(500) NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (incident_id),
  KEY idx_agent_control_state (control_state,updated_at),
  CONSTRAINT fk_agent_control_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_control_agent FOREIGN KEY (agent_id)
    REFERENCES monitoramento.agent_definitions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.agent_incident_control_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  incident_id BIGINT UNSIGNED NOT NULL,
  from_state ENUM('active','paused','human_owned') NOT NULL,
  to_state ENUM('active','paused','human_owned') NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  actor_name VARCHAR(150) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  correlation_id VARCHAR(100) NULL,
  version INT UNSIGNED NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_control_audit_idempotency (idempotency_key),
  KEY idx_agent_control_audit_incident (incident_id,occurred_at,id),
  CONSTRAINT fk_agent_control_audit_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
