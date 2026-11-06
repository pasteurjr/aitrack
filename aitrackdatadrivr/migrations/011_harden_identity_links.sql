-- UI-3.0C: impede duplicação do mesmo vínculo histórico em reprocessamentos.
CREATE UNIQUE INDEX IF NOT EXISTS uk_vinculo_origem_inicio
  ON monitoramento.veiculo_motorista_vinculos
    (vehicle_id, driver_id, fonte_codigo, valido_desde);
