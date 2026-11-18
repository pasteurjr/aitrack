-- UI-4.9: offline contextual considera integração, viagem/ignição e manutenção.

ALTER TABLE monitoramento.detector_episodes
  MODIFY episode_type ENUM('power_removed','low_external_voltage','offline') NOT NULL;

CREATE TABLE IF NOT EXISTS monitoramento.integration_health (
  source_code VARCHAR(30) NOT NULL,
  status ENUM('unknown','healthy','degraded','outage') NOT NULL DEFAULT 'unknown',
  last_success_at DATETIME(6) NULL,
  last_failure_at DATETIME(6) NULL,
  reason VARCHAR(500) NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (source_code),
  CONSTRAINT fk_integration_health_source FOREIGN KEY (source_code)
    REFERENCES monitoramento.fontes_dados(codigo) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.integration_health (source_code,status)
VALUES ('tracker','unknown'),('dirijabem','unknown');

CREATE TABLE IF NOT EXISTS monitoramento.vehicle_monitoring_context (
  vehicle_id BIGINT UNSIGNED NOT NULL,
  maintenance_until DATETIME(6) NULL,
  maintenance_reason VARCHAR(500) NULL,
  updated_by VARCHAR(100) NOT NULL DEFAULT 'migration-029',
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (vehicle_id),
  CONSTRAINT fk_vehicle_monitoring_context_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.offline_detector_state (
  policy_id BIGINT UNSIGNED NOT NULL,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  state ENUM('normal','suspect','offline','recovery_pending') NOT NULL DEFAULT 'normal',
  stale_checks SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  recovery_checks SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  active_episode_id BIGINT UNSIGNED NULL,
  last_position_at DATETIME(6) NULL,
  last_context VARCHAR(50) NULL,
  suppressed_reason VARCHAR(100) NULL,
  last_evaluated_at DATETIME(6) NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (policy_id,vehicle_id),
  KEY idx_offline_state_episode (active_episode_id),
  CONSTRAINT fk_offline_state_policy FOREIGN KEY (policy_id)
    REFERENCES monitoramento.detector_policies(id) ON DELETE RESTRICT,
  CONSTRAINT fk_offline_state_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.detector_policies
  (policy_key,version_number,detector_type,capability_code,scope_type,scope_ref,
   parameters_json,status,active_key,created_by,change_reason)
VALUES
  ('vehicle-offline',1,'offline','position','source','tracker',
   '{"expected_interval_seconds":5,"moving_grace_seconds":60,"ignition_grace_seconds":120,"idle_grace_seconds":600,"integration_outage_seconds":120,"trigger_checks":2,"recovery_checks":2,"severity":"high"}',
   'draft',NULL,'migration-029','Rascunho contextual; requer homologação e ativação.');
