-- UI-1.7: snapshot persistente do score comportamental atual.
-- A migration 005 permanece reservada para os índices de eventos do handoff.
CREATE TABLE IF NOT EXISTS tracker.behavioral_scores (
  device_id VARCHAR(50) PRIMARY KEY,
  veicod INT NULL,
  score DECIMAL(5,1) NOT NULL,
  janela_minutos SMALLINT UNSIGNED NOT NULL DEFAULT 60,
  eventos_na_janela INT UNSIGNED NOT NULL DEFAULT 0,
  calculado_em DATETIME(6) NOT NULL,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_behavioral_scores_veicod (veicod),
  INDEX idx_behavioral_scores_calculado (calculado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
