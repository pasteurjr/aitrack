-- UI-3.2: grupos, atribuições de cerca e janelas semanais por vínculo.
CREATE TABLE IF NOT EXISTS monitoramento.monitoring_groups (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  nome VARCHAR(150) NOT NULL,
  descricao TEXT NULL,
  owner_ref VARCHAR(100) NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_por VARCHAR(100) NOT NULL,
  atualizado_por VARCHAR(100) NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_monitoring_groups_public_id (public_id),
  UNIQUE KEY uk_monitoring_groups_owner_name (owner_ref, nome),
  KEY idx_monitoring_groups_active (ativo, atualizado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.monitoring_group_members (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  group_id BIGINT UNSIGNED NOT NULL,
  member_type ENUM('vehicle','driver') NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  adicionado_por VARCHAR(100) NOT NULL,
  adicionado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  removido_em DATETIME(6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_group_vehicle (group_id, vehicle_id),
  UNIQUE KEY uk_group_driver (group_id, driver_id),
  KEY idx_group_members_active (group_id, ativo),
  CONSTRAINT chk_group_member_exactly_one CHECK (
    (member_type = 'vehicle' AND vehicle_id IS NOT NULL AND driver_id IS NULL)
    OR
    (member_type = 'driver' AND driver_id IS NOT NULL AND vehicle_id IS NULL)
  ),
  CONSTRAINT fk_group_members_group
    FOREIGN KEY (group_id) REFERENCES monitoramento.monitoring_groups(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_group_members_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_group_members_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.geofence_assignments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  geofence_id BIGINT UNSIGNED NOT NULL,
  target_type ENUM('vehicle','driver','group') NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  driver_id BIGINT UNSIGNED NULL,
  group_id BIGINT UNSIGNED NULL,
  timezone_name VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo',
  effective_from DATE NULL,
  effective_to DATE NULL,
  notify_on_entry BOOLEAN NOT NULL DEFAULT FALSE,
  notify_on_exit BOOLEAN NOT NULL DEFAULT FALSE,
  dwell_threshold_seconds INT UNSIGNED NULL,
  hysteresis_meters DECIMAL(8,2) NOT NULL DEFAULT 30.00,
  cooldown_seconds INT UNSIGNED NOT NULL DEFAULT 300,
  priority SMALLINT UNSIGNED NOT NULL DEFAULT 100,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_por VARCHAR(100) NOT NULL,
  atualizado_por VARCHAR(100) NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_geofence_assignment_vehicle (geofence_id, vehicle_id),
  UNIQUE KEY uk_geofence_assignment_driver (geofence_id, driver_id),
  UNIQUE KEY uk_geofence_assignment_group (geofence_id, group_id),
  KEY idx_geofence_assignments_active (ativo, effective_from, effective_to),
  KEY idx_geofence_assignments_vehicle (vehicle_id, ativo),
  KEY idx_geofence_assignments_driver (driver_id, ativo),
  KEY idx_geofence_assignments_group (group_id, ativo),
  CONSTRAINT chk_geofence_assignment_exactly_one CHECK (
    (target_type = 'vehicle' AND vehicle_id IS NOT NULL
      AND driver_id IS NULL AND group_id IS NULL)
    OR
    (target_type = 'driver' AND driver_id IS NOT NULL
      AND vehicle_id IS NULL AND group_id IS NULL)
    OR
    (target_type = 'group' AND group_id IS NOT NULL
      AND vehicle_id IS NULL AND driver_id IS NULL)
  ),
  CONSTRAINT chk_geofence_assignment_dates CHECK (
    effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from
  ),
  CONSTRAINT chk_geofence_assignment_hysteresis CHECK (
    hysteresis_meters >= 0 AND hysteresis_meters <= 1000
  ),
  CONSTRAINT fk_geofence_assignments_geofence
    FOREIGN KEY (geofence_id) REFERENCES monitoramento.geofences(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_assignments_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_assignments_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_geofence_assignments_group
    FOREIGN KEY (group_id) REFERENCES monitoramento.monitoring_groups(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.geofence_assignment_schedules (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id BIGINT UNSIGNED NOT NULL,
  day_of_week TINYINT UNSIGNED NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  crosses_midnight BOOLEAN NOT NULL DEFAULT FALSE,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_assignment_schedule
    (assignment_id, day_of_week, start_time, end_time),
  KEY idx_assignment_schedules_active (assignment_id, ativo, day_of_week),
  CONSTRAINT chk_assignment_schedule_day CHECK (day_of_week BETWEEN 0 AND 6),
  CONSTRAINT chk_assignment_schedule_range CHECK (
    (crosses_midnight = FALSE AND end_time > start_time)
    OR
    (crosses_midnight = TRUE AND end_time <= start_time)
  ),
  CONSTRAINT fk_assignment_schedules_assignment
    FOREIGN KEY (assignment_id) REFERENCES monitoramento.geofence_assignments(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
