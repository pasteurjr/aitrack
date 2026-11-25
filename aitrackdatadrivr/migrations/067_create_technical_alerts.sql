-- UI-8.6: alertas técnicos internos, deduplicados e com recuperação explícita.
CREATE TABLE IF NOT EXISTS monitoramento.technical_alerts (
  alert_key VARCHAR(200) NOT NULL,
  component_key VARCHAR(100) NOT NULL,
  alert_type VARCHAR(100) NOT NULL,
  severity ENUM('warning','high','critical') NOT NULL,
  state ENUM('active','recovered') NOT NULL DEFAULT 'active',
  reason_code VARCHAR(100) NULL,
  summary VARCHAR(500) NOT NULL,
  opened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  last_observed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  recovered_at DATETIME(6) NULL,
  occurrence_count INT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY(alert_key),
  KEY idx_technical_alert_state(state,severity,last_observed_at),
  CONSTRAINT fk_technical_alert_component FOREIGN KEY(component_key)
    REFERENCES monitoramento.health_components(component_key) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.technical_alert_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  alert_key VARCHAR(200) NOT NULL,
  transition ENUM('opened','observed','recovered') NOT NULL,
  reason_code VARCHAR(100) NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id),
  KEY idx_technical_history(alert_key,occurred_at,id),
  CONSTRAINT fk_technical_history_alert FOREIGN KEY(alert_key)
    REFERENCES monitoramento.technical_alerts(alert_key) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
