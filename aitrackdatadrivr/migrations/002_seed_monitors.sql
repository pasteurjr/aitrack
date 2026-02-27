-- Migration 002: Seed Monitors and Distribute Vehicles
-- Creates 5 monitors and distributes 10 simulated vehicles among them

-- Insert 5 Monitores
INSERT INTO monitores (nome, descricao, tipo_monitor, intervalo_analise, janela_contexto, eventos_minimos, score_threshold, gera_alertas, ativo) VALUES
('Monitor #1', 'Monitora grupo de veículos analisando todos os eventos.', 'safety', 300, 1800, 3, 70.0, TRUE, TRUE),
('Monitor #2', 'Monitora grupo de veículos analisando todos os eventos.', 'efficiency', 600, 3600, 5, 75.0, TRUE, TRUE),
('Monitor #3', 'Monitora grupo de veículos analisando todos os eventos.', 'safety', 900, 5400, 4, 80.0, TRUE, TRUE),
('Monitor #4', 'Monitora grupo de veículos analisando todos os eventos.', 'compliance', 300, 1800, 2, 65.0, TRUE, TRUE),
('Monitor #5', 'Monitora grupo de veículos analisando todos os eventos.', 'predictive', 1800, 7200, 6, 70.0, FALSE, FALSE);

-- Distribuir Veículos entre Monitores
-- Monitor #1: 2 veículos (SIM-1000, SIM-1001) - VEICODs 1900, 1894
INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
SELECT 1, 'tracker', VEICOD, VEI_DEVICE_ID FROM veiculos
WHERE VEI_DEVICE_ID IN ('SIM-1000', 'SIM-1001');

-- Monitor #2: 2 veículos (SIM-1002, SIM-1003) - VEICODs 1895, 1901
INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
SELECT 2, 'tracker', VEICOD, VEI_DEVICE_ID FROM veiculos
WHERE VEI_DEVICE_ID IN ('SIM-1002', 'SIM-1003');

-- Monitor #3: 2 veículos (SIM-1004, SIM-1005) - VEICODs 1896, 1897
INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
SELECT 3, 'tracker', VEICOD, VEI_DEVICE_ID FROM veiculos
WHERE VEI_DEVICE_ID IN ('SIM-1004', 'SIM-1005');

-- Monitor #4: 3 veículos (SIM-1006, SIM-1007, SIM-1008) - VEICODs 1902, 1898, 1899
INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
SELECT 4, 'tracker', VEICOD, VEI_DEVICE_ID FROM veiculos
WHERE VEI_DEVICE_ID IN ('SIM-1006', 'SIM-1007', 'SIM-1008');

-- Monitor #5: 1 veículo (SIM-1009) - VEICOD 1903
INSERT INTO veiculomonitor (monitor_id, tipo_veiculo, veicod_tracker, device_id)
SELECT 5, 'tracker', VEICOD, VEI_DEVICE_ID FROM veiculos
WHERE VEI_DEVICE_ID = 'SIM-1009';
