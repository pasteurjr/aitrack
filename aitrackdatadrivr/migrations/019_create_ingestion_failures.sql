-- UI-3.8: retentativa e quarentena auditável da cauda Dirija Bem.
CREATE TABLE IF NOT EXISTS monitoramento.source_ingestion_failures (
  source_code VARCHAR(30) NOT NULL,
  stream_name VARCHAR(100) NOT NULL,
  external_position_id VARCHAR(100) NOT NULL,
  attempts SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  status ENUM('retry','quarantined') NOT NULL DEFAULT 'retry',
  last_error VARCHAR(1000) NOT NULL,
  first_failed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  last_failed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (source_code, stream_name, external_position_id),
  KEY idx_source_failures_status (source_code, stream_name, status, last_failed_at),
  CONSTRAINT fk_source_failure_source
    FOREIGN KEY (source_code) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
