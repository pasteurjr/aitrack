-- UI-4.10: contrato rastreável de comando, confirmação e timeout.

CREATE TABLE IF NOT EXISTS monitoramento.device_commands (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  source_code VARCHAR(30) NOT NULL,
  protocol_code VARCHAR(50) NOT NULL,
  capability_code VARCHAR(100) NOT NULL,
  status ENUM('requested','queued','sent','acknowledged','nacked','timed_out','cancelled','failed') NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  idempotency_key VARCHAR(150) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  payload_json LONGTEXT NOT NULL,
  requested_by_type ENUM('human','system','agent') NOT NULL,
  requested_by_id VARCHAR(100) NOT NULL,
  requested_by_name VARCHAR(150) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  provider_message_id VARCHAR(150) NULL,
  timeout_at DATETIME(6) NOT NULL,
  requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  sent_at DATETIME(6) NULL,
  finalized_at DATETIME(6) NULL,
  final_code VARCHAR(100) NULL,
  final_message VARCHAR(500) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_device_command_public (public_id),
  UNIQUE KEY uq_device_command_idempotency (source_code,idempotency_key),
  KEY idx_device_command_dispatch (status,timeout_at,id),
  KEY idx_device_command_vehicle (vehicle_id,requested_at DESC,id DESC),
  CONSTRAINT fk_device_command_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT fk_device_command_source FOREIGN KEY (source_code)
    REFERENCES monitoramento.fontes_dados(codigo) ON DELETE RESTRICT,
  CONSTRAINT chk_device_command_payload CHECK (JSON_VALID(payload_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.device_command_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  command_id BIGINT UNSIGNED NOT NULL,
  from_status ENUM('requested','queued','sent','acknowledged','nacked','timed_out','cancelled','failed') NULL,
  to_status ENUM('requested','queued','sent','acknowledged','nacked','timed_out','cancelled','failed') NOT NULL,
  actor_type ENUM('human','system','agent','provider') NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  event_code VARCHAR(100) NOT NULL,
  message VARCHAR(500) NULL,
  provider_message_id VARCHAR(150) NULL,
  correlation_id VARCHAR(100) NOT NULL,
  payload_json LONGTEXT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_device_command_event_correlation (command_id,correlation_id,event_code),
  KEY idx_device_command_events (command_id,occurred_at,id),
  CONSTRAINT fk_device_command_event_command FOREIGN KEY (command_id)
    REFERENCES monitoramento.device_commands(id) ON DELETE RESTRICT,
  CONSTRAINT chk_device_command_event_payload CHECK
    (payload_json IS NULL OR JSON_VALID(payload_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
