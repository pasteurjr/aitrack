-- UI-4.2: sensores operacionais e leituras imutáveis das duas fontes.
-- O catálogo descreve capacidade; esta estrutura registra instância e observação.

CREATE TABLE IF NOT EXISTS monitoramento.sensors (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vehicle_id BIGINT UNSIGNED NULL,
  source_code VARCHAR(30) NOT NULL,
  protocol_code VARCHAR(50) NOT NULL,
  device_model VARCHAR(100) NOT NULL DEFAULT '*',
  external_device_id VARCHAR(150) NOT NULL,
  capability_profile_item_id BIGINT UNSIGNED NULL,
  capability_code VARCHAR(100) NOT NULL,
  unit VARCHAR(30) NULL,
  lifecycle_status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  first_seen_at DATETIME(6) NOT NULL,
  last_seen_at DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_sensor_source_capability
    (source_code, protocol_code, external_device_id, capability_code),
  KEY idx_sensors_vehicle (vehicle_id, lifecycle_status, capability_code),
  CONSTRAINT fk_sensors_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT fk_sensors_source FOREIGN KEY (source_code)
    REFERENCES monitoramento.fontes_dados(codigo) ON DELETE RESTRICT,
  CONSTRAINT fk_sensors_capability FOREIGN KEY (capability_profile_item_id)
    REFERENCES monitoramento.capability_profile_items(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.sensor_readings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT UNSIGNED NOT NULL,
  source_code VARCHAR(30) NOT NULL,
  value_type ENUM('boolean','number','string','geo','json') NOT NULL,
  value_json LONGTEXT NOT NULL,
  unit VARCHAR(30) NULL,
  quality ENUM('valid','invalid','estimated','unknown') NOT NULL,
  observed_at DATETIME(6) NOT NULL,
  received_at DATETIME(6) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  source_record_id VARCHAR(150) NULL,
  metadata_json LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_sensor_reading_correlation (sensor_id, correlation_id),
  KEY idx_sensor_readings_timeline (sensor_id, observed_at DESC, id DESC),
  KEY idx_sensor_readings_source_time (source_code, received_at DESC),
  CONSTRAINT fk_sensor_readings_sensor FOREIGN KEY (sensor_id)
    REFERENCES monitoramento.sensors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_sensor_readings_source FOREIGN KEY (source_code)
    REFERENCES monitoramento.fontes_dados(codigo) ON DELETE RESTRICT,
  CONSTRAINT chk_sensor_reading_value_json CHECK (JSON_VALID(value_json)),
  CONSTRAINT chk_sensor_reading_metadata_json CHECK
    (metadata_json IS NULL OR JSON_VALID(metadata_json)),
  CONSTRAINT chk_sensor_reading_times CHECK (received_at >= observed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
