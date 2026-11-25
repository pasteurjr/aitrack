-- UI-7.8: EXPLAIN mostrou scan de índice sem chave temporal inicial.
CREATE INDEX IF NOT EXISTS idx_incidents_opened_at
  ON monitoramento.incidents(opened_at, id);
