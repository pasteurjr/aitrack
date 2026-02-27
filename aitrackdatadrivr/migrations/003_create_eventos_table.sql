-- Migration 003: Create Event Tables
-- Creates tipo_evento catalog and eventos table for persistent event storage

-- Tabela de tipos de eventos (catálogo)
CREATE TABLE IF NOT EXISTS tipo_evento (
  id INT PRIMARY KEY AUTO_INCREMENT,
  codigo VARCHAR(50) UNIQUE NOT NULL,
  nome VARCHAR(100) NOT NULL,
  categoria ENUM('critical', 'behavioral', 'operational') NOT NULL,
  severidade_padrao ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  icone VARCHAR(10),
  cor VARCHAR(10),
  descricao TEXT,
  INDEX idx_categoria (categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Popular com 4 eventos já implementados no behavioral_engine
INSERT INTO tipo_evento (codigo, nome, categoria, severidade_padrao, icone, cor, descricao) VALUES
('harsh_brake', 'Frenagem Brusca', 'behavioral', 'high', 'brake', '#f59e0b', 'Desaceleração superior a 20 km/h em curto intervalo'),
('harsh_accel', 'Aceleração Brusca', 'behavioral', 'medium', 'accel', '#f59e0b', 'Aceleração superior a 15 km/h em curto intervalo'),
('speeding', 'Excesso de Velocidade', 'behavioral', 'high', 'speed', '#ea580c', 'Velocidade acima do limite permitido'),
('sharp_turn', 'Curva Acentuada', 'behavioral', 'medium', 'turn', '#f59e0b', 'Mudança de direção superior a 45° em alta velocidade');

-- Tabela de eventos ocorridos
CREATE TABLE IF NOT EXISTS eventos (
  id INT PRIMARY KEY AUTO_INCREMENT,
  tipo_evento_id INT NOT NULL,
  veicod INT NOT NULL,
  device_id VARCHAR(50),
  timestamp DATETIME NOT NULL,
  latitude DOUBLE,
  longitude DOUBLE,
  velocidade FLOAT,
  dados_adicionais JSON,
  severidade ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  processado BOOLEAN DEFAULT FALSE,

  FOREIGN KEY (tipo_evento_id) REFERENCES tipo_evento(id),
  FOREIGN KEY (veicod) REFERENCES veiculos(VEICOD),

  INDEX idx_timestamp (timestamp),
  INDEX idx_device (device_id),
  INDEX idx_processado (processado),
  INDEX idx_veicod (veicod)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
