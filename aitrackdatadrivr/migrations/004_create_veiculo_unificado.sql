-- Migration 004: Tabela veiculo_unificado
-- Ponte entre banco tracker e banco dirijabem
-- Permite que um veículo tenha rastreador GPS (tracker), app celular (dirijabem), ou ambos

USE tracker;

CREATE TABLE IF NOT EXISTS veiculo_unificado (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Identificadores (links para os bancos)
    device_id VARCHAR(50) NULL,              -- Link para tracker: veiculos.VEI_DEVICE_ID
    codusu INT NULL,                         -- Link para dirijabem: usuario.CODUSU

    -- Informações do veículo
    placa VARCHAR(20) NULL,
    descricao VARCHAR(200) NULL,

    -- Tipo de fonte de dados
    tipo ENUM('tracker_only', 'app_only', 'both') DEFAULT 'tracker_only',

    -- Metadados
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Índices para busca rápida
    INDEX idx_device_id (device_id),
    INDEX idx_codusu (codusu),
    INDEX idx_placa (placa),
    INDEX idx_tipo (tipo),
    INDEX idx_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Popular com veículos do tracker (simulados)
INSERT INTO veiculo_unificado (device_id, placa, tipo, descricao) VALUES
('SIM-1000', 'SIM-1000', 'tracker_only', 'Veículo simulado rastreador GPS 1'),
('SIM-1001', 'SIM-1001', 'tracker_only', 'Veículo simulado rastreador GPS 2'),
('SIM-1002', 'SIM-1002', 'tracker_only', 'Veículo simulado rastreador GPS 3'),
('SIM-1003', 'SIM-1003', 'tracker_only', 'Veículo simulado rastreador GPS 4'),
('SIM-1004', 'SIM-1004', 'tracker_only', 'Veículo simulado rastreador GPS 5'),
('SIM-1005', 'SIM-1005', 'tracker_only', 'Veículo simulado rastreador GPS 6'),
('SIM-1006', 'SIM-1006', 'tracker_only', 'Veículo simulado rastreador GPS 7'),
('SIM-1007', 'SIM-1007', 'tracker_only', 'Veículo simulado rastreador GPS 8'),
('SIM-1008', 'SIM-1008', 'tracker_only', 'Veículo simulado rastreador GPS 9'),
('SIM-1009', 'SIM-1009', 'tracker_only', 'Veículo simulado rastreador GPS 10');

-- Popular com veículos do dirijabem (simulados)
INSERT INTO veiculo_unificado (codusu, placa, tipo, descricao) VALUES
(1, 'SIM-D1', 'app_only', 'Veículo simulado app Dirijabem 1 (CODUSU 1)'),
(614, 'SIM-D2', 'app_only', 'Veículo simulado app Dirijabem 2 (CODUSU 614)'),
(17, 'SIM-D3', 'app_only', 'Veículo simulado app Dirijabem 3 (CODUSU 17)'),
(411, 'SIM-D4', 'app_only', 'Veículo simulado app Dirijabem 4 (CODUSU 411)'),
(21, 'SIM-D5', 'app_only', 'Veículo simulado app Dirijabem 5 (CODUSU 21)'),
(239, 'SIM-D6', 'app_only', 'Veículo simulado app Dirijabem 6 (CODUSU 239)'),
(617, 'SIM-D7', 'app_only', 'Veículo simulado app Dirijabem 7 (CODUSU 617)'),
(608, 'SIM-D8', 'app_only', 'Veículo simulado app Dirijabem 8 (CODUSU 608)'),
(36, 'SIM-D9', 'app_only', 'Veículo simulado app Dirijabem 9 (CODUSU 36)'),
(70, 'SIM-D10', 'app_only', 'Veículo simulado app Dirijabem 10 (CODUSU 70)');

-- Exemplo de veículo com AMBOS (descomentar se quiser testar)
-- INSERT INTO veiculo_unificado (device_id, codusu, placa, tipo, descricao) VALUES
-- ('SIM-1000', 1, 'ABC1234', 'both', 'Veículo com rastreador E app');

SELECT 'Migration 004 completed: veiculo_unificado table created and populated' as status;
