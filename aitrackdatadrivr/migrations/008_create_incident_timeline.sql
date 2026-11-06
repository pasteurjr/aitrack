-- UI-2.2: histórico auditável e append-only de cada incidente.
CREATE TABLE IF NOT EXISTS tracker.incident_timeline (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  incident_id BIGINT UNSIGNED NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  entry_type VARCHAR(50) NOT NULL,

  actor_type ENUM('system', 'human', 'agent', 'integration') NOT NULL,
  actor_id VARCHAR(100) NULL,
  actor_name VARCHAR(150) NULL,

  from_status ENUM(
    'new', 'triage', 'in_progress', 'waiting_response',
    'escalated', 'resolved', 'closed'
  ) NULL,
  to_status ENUM(
    'new', 'triage', 'in_progress', 'waiting_response',
    'escalated', 'resolved', 'closed'
  ) NULL,

  summary VARCHAR(300) NOT NULL,
  details JSON NULL,
  event_id INT NULL,
  evidence_type VARCHAR(50) NULL,
  evidence_ref VARCHAR(150) NULL,
  correlation_id VARCHAR(100) NULL,
  causation_id VARCHAR(100) NULL,
  visibility ENUM('internal', 'customer') NOT NULL DEFAULT 'internal',

  occurred_at DATETIME(6) NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  PRIMARY KEY (id),
  UNIQUE KEY uk_incident_timeline_idempotency (idempotency_key),
  KEY idx_incident_timeline_order (incident_id, occurred_at, id),
  KEY idx_incident_timeline_type (incident_id, entry_type, occurred_at),
  KEY idx_incident_timeline_event (event_id),
  KEY idx_incident_timeline_correlation (correlation_id),
  CONSTRAINT fk_incident_timeline_incident
    FOREIGN KEY (incident_id) REFERENCES tracker.incidents(id),
  CONSTRAINT fk_incident_timeline_event
    FOREIGN KEY (event_id) REFERENCES tracker.eventos(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
