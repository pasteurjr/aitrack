-- UI-4.7: estado patrimonial armado/desarmado por veículo e histórico imutável.

CREATE TABLE IF NOT EXISTS monitoramento.vehicle_security_state (
  vehicle_id BIGINT UNSIGNED NOT NULL,
  state ENUM('disarmed','armed') NOT NULL DEFAULT 'disarmed',
  version INT UNSIGNED NOT NULL DEFAULT 1,
  changed_by_type ENUM('human','system') NOT NULL,
  changed_by_id VARCHAR(100) NOT NULL,
  changed_by_name VARCHAR(150) NOT NULL,
  authorization_basis ENUM('owner_request','operator_protocol','scheduled_policy','migration') NOT NULL,
  reason VARCHAR(500) NOT NULL,
  changed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (vehicle_id),
  CONSTRAINT fk_vehicle_security_state_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.vehicle_security_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  from_state ENUM('disarmed','armed') NOT NULL,
  to_state ENUM('disarmed','armed') NOT NULL,
  from_version INT UNSIGNED NOT NULL,
  to_version INT UNSIGNED NOT NULL,
  actor_type ENUM('human','system') NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  actor_name VARCHAR(150) NOT NULL,
  authorization_basis ENUM('owner_request','operator_protocol','scheduled_policy') NOT NULL,
  reason VARCHAR(500) NOT NULL,
  correlation_id VARCHAR(100) NOT NULL,
  occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_vehicle_security_correlation (vehicle_id, correlation_id),
  KEY idx_vehicle_security_history (vehicle_id, occurred_at DESC, id DESC),
  CONSTRAINT fk_vehicle_security_history_vehicle FOREIGN KEY (vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.vehicle_security_state
  (vehicle_id, state, version, changed_by_type, changed_by_id, changed_by_name,
   authorization_basis, reason)
SELECT id, 'disarmed', 1, 'system', 'migration-027', 'Migration UI-4.7',
       'migration', 'Estado inicial seguro; nenhuma política patrimonial ativada.'
  FROM monitoramento.veiculos
 WHERE merged_into_id IS NULL;
