-- UI-3.0E2: alvos de monitoramento distinguem veículo de motorista.
CREATE TABLE IF NOT EXISTS monitoramento.monitor_targets (
  id INT NOT NULL AUTO_INCREMENT,
  monitor_id INT NOT NULL,
  target_type ENUM('vehicle','driver') NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  fonte_codigo VARCHAR(30) NOT NULL,
  legacy_veiculomonitor_id INT NULL,
  legacy_veicod_tracker INT NULL,
  legacy_codusu_dirijabem INT NULL,
  legacy_device_id VARCHAR(50) NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  atribuido_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_monitor_target_vehicle (monitor_id, vehicle_id),
  UNIQUE KEY uk_monitor_target_driver (monitor_id, driver_id),
  KEY idx_monitor_targets_active (monitor_id, ativo),
  KEY idx_monitor_targets_vehicle (vehicle_id, ativo),
  KEY idx_monitor_targets_driver (driver_id, ativo),
  CONSTRAINT chk_monitor_target_exactly_one CHECK (
    (target_type = 'vehicle' AND vehicle_id IS NOT NULL AND driver_id IS NULL)
    OR
    (target_type = 'driver' AND driver_id IS NOT NULL AND vehicle_id IS NULL)
  ),
  CONSTRAINT fk_monitor_targets_monitor
    FOREIGN KEY (monitor_id) REFERENCES monitoramento.monitores(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_monitor_targets_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_monitor_targets_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_monitor_targets_source
    FOREIGN KEY (fonte_codigo) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.monitor_analises (
  id INT NOT NULL AUTO_INCREMENT,
  monitor_id INT NOT NULL,
  monitor_target_id INT NOT NULL,
  analisado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  periodo_inicio DATETIME(6) NOT NULL,
  periodo_fim DATETIME(6) NOT NULL,
  total_eventos INT NOT NULL DEFAULT 0,
  score_inicial FLOAT NULL,
  score_final FLOAT NULL,
  eventos_por_tipo JSON NULL,
  conclusao TEXT NULL,
  severidade ENUM('low','medium','high','critical') NULL,
  PRIMARY KEY (id),
  KEY idx_monitor_analises_target (monitor_target_id, analisado_em),
  KEY idx_monitor_analises_monitor (monitor_id, analisado_em),
  CONSTRAINT fk_monitor_analises_monitor
    FOREIGN KEY (monitor_id) REFERENCES monitoramento.monitores(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_monitor_analises_target
    FOREIGN KEY (monitor_target_id) REFERENCES monitoramento.monitor_targets(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.monitor_alertas (
  id INT NOT NULL AUTO_INCREMENT,
  analise_id INT NULL,
  monitor_id INT NOT NULL,
  monitor_target_id INT NOT NULL,
  device_id VARCHAR(50) NULL,
  nome_motorista VARCHAR(100) NULL,
  titulo VARCHAR(200) NOT NULL,
  mensagem TEXT NULL,
  severidade ENUM('low','medium','high','critical') NOT NULL,
  tipo ENUM('behavior','safety','efficiency','compliance','prediction')
    NOT NULL DEFAULT 'behavior',
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  status ENUM('pending','acknowledged','resolved','dismissed')
    NOT NULL DEFAULT 'pending',
  reconhecido_em DATETIME(6) NULL,
  reconhecido_por VARCHAR(100) NULL,
  total_eventos_relacionados INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_monitor_alertas_analysis (analise_id),
  KEY idx_monitor_alertas_target (monitor_target_id),
  KEY idx_monitor_alertas_status (status),
  KEY idx_monitor_alertas_monitor (monitor_id),
  KEY idx_monitor_alertas_created (criado_em),
  CONSTRAINT fk_monitor_alertas_analysis
    FOREIGN KEY (analise_id) REFERENCES monitoramento.monitor_analises(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_monitor_alertas_monitor
    FOREIGN KEY (monitor_id) REFERENCES monitoramento.monitores(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_monitor_alertas_target
    FOREIGN KEY (monitor_target_id) REFERENCES monitoramento.monitor_targets(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
