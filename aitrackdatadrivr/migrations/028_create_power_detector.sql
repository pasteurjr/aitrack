-- UI-4.8: episódios de alimentação removida/baixa tensão externa com histerese.

CREATE TABLE IF NOT EXISTS monitoramento.detector_signal_state (
  policy_id BIGINT UNSIGNED NOT NULL,
  sensor_id BIGINT UNSIGNED NOT NULL,
  state ENUM('normal','trigger_pending','active','recovery_pending') NOT NULL DEFAULT 'normal',
  trigger_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  recovery_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  active_episode_id BIGINT UNSIGNED NULL,
  last_reading_id BIGINT UNSIGNED NULL,
  last_value DECIMAL(12,4) NULL,
  cooldown_until DATETIME(6) NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (policy_id, sensor_id),
  KEY idx_detector_signal_episode (active_episode_id),
  CONSTRAINT fk_detector_signal_policy FOREIGN KEY (policy_id)
    REFERENCES monitoramento.detector_policies(id) ON DELETE RESTRICT,
  CONSTRAINT fk_detector_signal_sensor FOREIGN KEY (sensor_id)
    REFERENCES monitoramento.sensors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_detector_signal_reading FOREIGN KEY (last_reading_id)
    REFERENCES monitoramento.sensor_readings(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.detector_episodes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  policy_id BIGINT UNSIGNED NOT NULL,
  sensor_id BIGINT UNSIGNED NOT NULL,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  episode_type ENUM('power_removed','low_external_voltage') NOT NULL,
  status ENUM('open','resolved') NOT NULL,
  severity ENUM('info','low','medium','high','critical') NOT NULL,
  correlation_key VARCHAR(180) NOT NULL,
  started_at DATETIME(6) NOT NULL,
  resolved_at DATETIME(6) NULL,
  trigger_value DECIMAL(12,4) NOT NULL,
  recovery_value DECIMAL(12,4) NULL,
  minimum_value DECIMAL(12,4) NOT NULL,
  evidence_count INT UNSIGNED NOT NULL DEFAULT 1,
  metadata_json LONGTEXT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_detector_episode_public (public_id),
  UNIQUE KEY uq_detector_episode_correlation (correlation_key),
  KEY idx_detector_episode_vehicle (vehicle_id, status, started_at DESC),
  CONSTRAINT fk_detector_episode_policy FOREIGN KEY (policy_id)
    REFERENCES monitoramento.detector_policies(id) ON DELETE RESTRICT,
  CONSTRAINT fk_detector_episode_sensor FOREIGN KEY (sensor_id)
    REFERENCES monitoramento.sensors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_detector_episode_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT chk_detector_episode_metadata CHECK (JSON_VALID(metadata_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Políticas conservadoras nascem em draft. Nada é detectado até ativação explícita.
INSERT IGNORE INTO monitoramento.detector_policies
  (policy_key,version_number,detector_type,capability_code,scope_type,scope_ref,
   parameters_json,status,active_key,created_by,change_reason)
VALUES
  ('power-removed',1,'power_removed','external_voltage','source','tracker',
   '{"trigger_below_v":2.0,"recover_above_v":8.0,"trigger_samples":2,"recover_samples":2,"cooldown_seconds":900,"severity":"critical"}',
   'draft',NULL,'migration-028','Rascunho conservador; requer homologação e ativação.'),
  ('low-external-voltage',1,'low_external_voltage','external_voltage','source','tracker',
   '{"trigger_above_v":2.0,"trigger_below_v":11.6,"recover_above_v":12.2,"trigger_samples":3,"recover_samples":3,"cooldown_seconds":1800,"severity":"high"}',
   'draft',NULL,'migration-028','Tensão externa, não bateria interna; requer homologação e ativação.');
