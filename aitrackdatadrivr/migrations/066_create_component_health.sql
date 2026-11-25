-- UI-8.5: saúde consolidada e histórico de transições técnicas.
CREATE TABLE IF NOT EXISTS monitoramento.health_components (
  component_key VARCHAR(100) NOT NULL,
  component_type ENUM('database','ingestion','worker','provider','channel') NOT NULL,
  display_name VARCHAR(150) NOT NULL,
  critical BOOLEAN NOT NULL DEFAULT FALSE,
  status ENUM('unknown','healthy','degraded','outage') NOT NULL DEFAULT 'unknown',
  heartbeat_at DATETIME(6) NULL,
  last_success_at DATETIME(6) NULL,
  last_failure_at DATETIME(6) NULL,
  latency_ms INT UNSIGNED NULL,
  lag_seconds INT UNSIGNED NULL,
  queue_depth INT UNSIGNED NULL,
  oldest_item_seconds INT UNSIGNED NULL,
  reason_code VARCHAR(100) NULL,
  reason_sanitized VARCHAR(500) NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY(component_key),
  KEY idx_health_status(status,critical,updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.health_transitions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  component_key VARCHAR(100) NOT NULL,
  from_status ENUM('unknown','healthy','degraded','outage') NOT NULL,
  to_status ENUM('unknown','healthy','degraded','outage') NOT NULL,
  reason_code VARCHAR(100) NULL,
  reason_sanitized VARCHAR(500) NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id),
  KEY idx_health_transition_component(component_key,occurred_at,id),
  CONSTRAINT fk_health_transition_component FOREIGN KEY(component_key)
    REFERENCES monitoramento.health_components(component_key) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.health_components
  (component_key,component_type,display_name,critical)
VALUES
  ('database','database','Banco operacional',TRUE),
  ('tracker_ingestion','ingestion','Ingestão Tracker',TRUE),
  ('dirijabem_ingestion','ingestion','Ingestão Dirija Bem',TRUE),
  ('agent_worker','worker','Worker de agentes',FALSE),
  ('action_worker','worker','Worker de ações',TRUE),
  ('report_worker','worker','Worker de relatórios',FALSE),
  ('ai_provider','provider','Provedor de IA',FALSE),
  ('message_provider','channel','Canal de mensagens',FALSE),
  ('voice_provider','channel','Canal de voz',FALSE);
