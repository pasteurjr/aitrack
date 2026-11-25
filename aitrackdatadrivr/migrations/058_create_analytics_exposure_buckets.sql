-- UI-7.6: exposição operacional comum, sem escrita nas fontes Tracker/Dirija Bem.
CREATE TABLE IF NOT EXISTS monitoramento.analytics_exposure_buckets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source VARCHAR(30) NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  external_vehicle_ref VARCHAR(150) NOT NULL,
  bucket_start DATETIME(6) NOT NULL,
  bucket_end DATETIME(6) NOT NULL,
  distance_km DECIMAL(14,6) NOT NULL DEFAULT 0,
  driving_seconds INT UNSIGNED NOT NULL DEFAULT 0,
  valid_points INT UNSIGNED NOT NULL DEFAULT 0,
  discarded_points INT UNSIGNED NOT NULL DEFAULT 0,
  quality ENUM('complete','partial','unavailable') NOT NULL,
  formula_version VARCHAR(50) NOT NULL,
  materialized_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id),
  UNIQUE KEY uq_exposure_bucket(source,external_vehicle_ref,bucket_start,formula_version),
  KEY idx_exposure_period(source,bucket_start,bucket_end),
  KEY idx_exposure_vehicle(vehicle_id,bucket_start),
  CONSTRAINT fk_exposure_vehicle FOREIGN KEY(vehicle_id)
    REFERENCES monitoramento.veiculos(id) ON DELETE RESTRICT,
  CONSTRAINT chk_exposure_interval CHECK(bucket_end>bucket_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.analytics_materialization_offsets (
  source VARCHAR(30) NOT NULL,
  stream_key VARCHAR(100) NOT NULL,
  watermark_value VARCHAR(200) NULL,
  last_success_at DATETIME(6) NULL,
  last_error_at DATETIME(6) NULL,
  last_error_code VARCHAR(100) NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY(source,stream_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
