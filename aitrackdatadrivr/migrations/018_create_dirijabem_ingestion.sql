-- UI-3.8: consumo incremental e idempotente de posições externas Dirija Bem.
ALTER TABLE monitoramento.geofence_events
  ADD COLUMN IF NOT EXISTS received_at DATETIME(6) NOT NULL
    DEFAULT CURRENT_TIMESTAMP(6) AFTER observed_at,
  ADD KEY IF NOT EXISTS idx_geofence_events_received (received_at, id);

CREATE TABLE IF NOT EXISTS monitoramento.source_ingestion_offsets (
  source_code VARCHAR(30) NOT NULL,
  stream_name VARCHAR(100) NOT NULL,
  last_external_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (source_code, stream_name),
  CONSTRAINT fk_source_offset_source
    FOREIGN KEY (source_code) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.source_position_receipts (
  source_code VARCHAR(30) NOT NULL,
  external_position_id VARCHAR(100) NOT NULL,
  received_at DATETIME(6) NOT NULL,
  processed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (source_code, external_position_id),
  KEY idx_source_receipts_processed (processed_at),
  CONSTRAINT fk_source_receipt_source
    FOREIGN KEY (source_code) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
