-- UI-3.0E1: incidentes passam a pertencer à camada operacional unificada.
CREATE TABLE IF NOT EXISTS monitoramento.monitores (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  descricao TEXT NULL,
  tipo_monitor ENUM('safety','efficiency','compliance','predictive','custom')
    NOT NULL DEFAULT 'safety',
  intervalo_analise INT NOT NULL DEFAULT 300,
  janela_contexto INT NOT NULL DEFAULT 1800,
  eventos_minimos INT NOT NULL DEFAULT 3,
  score_threshold FLOAT NOT NULL DEFAULT 70,
  gera_alertas BOOLEAN NOT NULL DEFAULT TRUE,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_monitores_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.incidents (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  correlation_key VARCHAR(150) NOT NULL,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  legacy_vehicle_id INT NULL,
  monitor_id INT NULL,
  origin_episode_id VARCHAR(64) NULL,
  incident_type VARCHAR(50) NOT NULL,
  title VARCHAR(200) NOT NULL,
  summary TEXT NULL,
  status ENUM(
    'new','triage','in_progress','waiting_response','escalated','resolved','closed'
  ) NOT NULL DEFAULT 'new',
  severity ENUM('low','medium','high','critical') NOT NULL,
  risk_score DECIMAL(5,2) NULL,
  primary_source ENUM('tracker','dirijabem','fused','system') NOT NULL,
  driver_ref VARCHAR(100) NULL,
  owner_ref VARCHAR(100) NULL,
  assigned_type ENUM('human','agent') NULL,
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
  detection_outcome ENUM(
    'unreviewed','true_positive','false_positive','false_negative'
  ) NOT NULL DEFAULT 'unreviewed',
  classification_reason VARCHAR(50) NULL,
  classified_by VARCHAR(100) NULL,
  classified_at DATETIME(6) NULL,
  event_count INT UNSIGNED NOT NULL DEFAULT 0,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_incidents_correlation (correlation_key),
  KEY idx_incidents_vehicle_status (vehicle_id, status, updated_at),
  KEY idx_incidents_legacy_vehicle (legacy_vehicle_id),
  KEY idx_incidents_status_severity (status, severity, opened_at),
  KEY idx_incidents_monitor (monitor_id, status),
  KEY idx_incidents_assignee (assigned_type, assigned_to, status),
  KEY idx_incidents_sla (status, sla_due_at),
  KEY idx_incidents_episode (origin_episode_id),
  KEY idx_incidents_detection_outcome (detection_outcome, classified_at),
  CONSTRAINT fk_operational_incidents_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_operational_incidents_monitor
    FOREIGN KEY (monitor_id) REFERENCES monitoramento.monitores(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.incident_timeline (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  incident_id BIGINT UNSIGNED NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  entry_type VARCHAR(50) NOT NULL,
  actor_type ENUM('system','human','agent','integration') NOT NULL,
  actor_id VARCHAR(100) NULL,
  actor_name VARCHAR(150) NULL,
  from_status ENUM(
    'new','triage','in_progress','waiting_response','escalated','resolved','closed'
  ) NULL,
  to_status ENUM(
    'new','triage','in_progress','waiting_response','escalated','resolved','closed'
  ) NULL,
  summary VARCHAR(300) NOT NULL,
  details JSON NULL,
  event_id INT NULL,
  event_source VARCHAR(30) NULL,
  evidence_type VARCHAR(50) NULL,
  evidence_ref VARCHAR(150) NULL,
  correlation_id VARCHAR(100) NULL,
  causation_id VARCHAR(100) NULL,
  visibility ENUM('internal','customer') NOT NULL DEFAULT 'internal',
  occurred_at DATETIME(6) NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_incident_timeline_idempotency (idempotency_key),
  KEY idx_incident_timeline_order (incident_id, occurred_at, id),
  KEY idx_incident_timeline_type (incident_id, entry_type, occurred_at),
  KEY idx_incident_timeline_event (event_source, event_id),
  KEY idx_incident_timeline_correlation (correlation_id),
  CONSTRAINT fk_operational_timeline_incident
    FOREIGN KEY (incident_id) REFERENCES monitoramento.incidents(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
