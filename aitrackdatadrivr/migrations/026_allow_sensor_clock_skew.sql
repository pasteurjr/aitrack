-- UI-4.5: o relógio do equipamento pode usar fuso/desvio diferente do servidor.
-- Preservar os dois instantes é mais seguro do que alterar silenciosamente a fonte.
ALTER TABLE monitoramento.sensor_readings
  DROP CONSTRAINT chk_sensor_reading_times;
