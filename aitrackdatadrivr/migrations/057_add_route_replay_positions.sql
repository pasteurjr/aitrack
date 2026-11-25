-- UI-7.4: coordenadas mínimas para replay somente leitura por execução.
ALTER TABLE monitoramento.route_position_receipts
  ADD COLUMN IF NOT EXISTS longitude DOUBLE NULL AFTER observed_at,
  ADD COLUMN IF NOT EXISTS latitude DOUBLE NULL AFTER longitude,
  ADD COLUMN IF NOT EXISTS speed_kmh DECIMAL(8,2) NULL AFTER latitude;

CREATE INDEX IF NOT EXISTS idx_route_position_time
  ON monitoramento.route_position_receipts(execution_id, observed_at, id);
