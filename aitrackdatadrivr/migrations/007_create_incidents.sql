-- UI-2.1: entidade operacional de incidentes.
-- A migration 005 permanece reservada para índices de eventos.
CREATE TABLE IF NOT EXISTS tracker.incidents (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  correlation_key VARCHAR(150) NOT NULL,
  vehicle_id INT NOT NULL,
  monitor_id INT NULL,
  origin_episode_id VARCHAR(64) NULL,

  incident_type VARCHAR(50) NOT NULL,
  title VARCHAR(200) NOT NULL,
  summary TEXT NULL,
  status ENUM(
    'new',
    'triage',
    'in_progress',
    'waiting_response',
    'escalated',
    'resolved',
    'closed'
  ) NOT NULL DEFAULT 'new',
  severity ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  risk_score DECIMAL(5,2) NULL,
  primary_source ENUM('tracker', 'dirijabem', 'fused', 'system') NOT NULL,

  driver_ref VARCHAR(100) NULL,
  owner_ref VARCHAR(100) NULL,
  assigned_type ENUM('human', 'agent') NULL,
  assigned_to VARCHAR(100) NULL,

  latitude DOUBLE NULL,
  longitude DOUBLE NULL,
  position_observed_at DATETIME(6) NULL,
  hypothesis TEXT NULL,
  confidence DECIMAL(5,4) NULL,
  context_snapshot JSON NULL,

  opened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  triaged_at DATETIME(6) NULL,
  acknowledged_at DATETIME(6) NULL,
  sla_due_at DATETIME(6) NULL,
  next_action_at DATETIME(6) NULL,
  resolved_at DATETIME(6) NULL,
  closed_at DATETIME(6) NULL,

  resolution_code VARCHAR(50) NULL,
  resolution_notes TEXT NULL,
  false_positive BOOLEAN NOT NULL DEFAULT FALSE,
  event_count INT UNSIGNED NOT NULL DEFAULT 0,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),

  PRIMARY KEY (id),
  UNIQUE KEY uk_incidents_correlation (correlation_key),
  KEY idx_incidents_vehicle_status (vehicle_id, status, updated_at),
  KEY idx_incidents_status_severity (status, severity, opened_at),
  KEY idx_incidents_monitor (monitor_id, status),
  KEY idx_incidents_assignee (assigned_type, assigned_to, status),
  KEY idx_incidents_sla (status, sla_due_at),
  KEY idx_incidents_episode (origin_episode_id),
  CONSTRAINT fk_incidents_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES tracker.veiculo_unificado(id),
  CONSTRAINT fk_incidents_monitor
    FOREIGN KEY (monitor_id) REFERENCES tracker.monitores(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
