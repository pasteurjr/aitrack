-- Migration 001: Create Monitor Tables
-- Creates 4 tables for AI Monitor system: monitores, veiculomonitor, monitor_analises, monitor_alertas

-- Tabela 1: Monitores AI
CREATE TABLE IF NOT EXISTS monitores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  descricao TEXT,
  tipo_monitor ENUM('safety', 'efficiency', 'compliance', 'predictive', 'custom') DEFAULT 'safety',

  -- Configuração (simplificada - LLM vem depois)
  intervalo_analise INT DEFAULT 300,
  janela_contexto INT DEFAULT 1800,
  eventos_minimos INT DEFAULT 3,
  score_threshold FLOAT DEFAULT 70.0,
  gera_alertas BOOLEAN DEFAULT TRUE,

  -- Estado
  ativo BOOLEAN DEFAULT TRUE,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela 2: Associação Veículo-Monitor
CREATE TABLE IF NOT EXISTS veiculomonitor (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL,
  tipo_veiculo ENUM('tracker', 'dirijabem') NOT NULL,
  veicod_tracker INT NULL,
  codusu_dirijabem INT NULL,
  device_id VARCHAR(50),
  ativo BOOLEAN DEFAULT TRUE,
  atribuido_em DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,
  FOREIGN KEY (veicod_tracker) REFERENCES veiculos(VEICOD) ON DELETE CASCADE,

  UNIQUE KEY uk_monitor_tracker (monitor_id, veicod_tracker),
  UNIQUE KEY uk_monitor_dirijabem (monitor_id, codusu_dirijabem),

  INDEX idx_monitor (monitor_id),
  INDEX idx_device (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela 3: Análises (simplificada - sem LLM por enquanto)
CREATE TABLE IF NOT EXISTS monitor_analises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL,
  analisado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  periodo_inicio DATETIME NOT NULL,
  periodo_fim DATETIME NOT NULL,

  -- Contexto
  total_eventos INT DEFAULT 0,
  score_inicial FLOAT,
  score_final FLOAT,
  eventos_por_tipo JSON,

  -- Resultado (simplificado)
  conclusao TEXT,
  severidade ENUM('low', 'medium', 'high', 'critical'),

  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,
  FOREIGN KEY (veiculomonitor_id) REFERENCES veiculomonitor(id) ON DELETE CASCADE,

  INDEX idx_monitor_data (monitor_id, analisado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela 4: Alertas
CREATE TABLE IF NOT EXISTS monitor_alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  analise_id INT NULL,
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL,
  device_id VARCHAR(50),
  nome_motorista VARCHAR(100),

  titulo VARCHAR(200) NOT NULL,
  mensagem TEXT,
  severidade ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  tipo ENUM('behavior', 'safety', 'efficiency', 'compliance', 'prediction') DEFAULT 'behavior',

  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('pending', 'acknowledged', 'resolved', 'dismissed') DEFAULT 'pending',
  reconhecido_em DATETIME NULL,
  reconhecido_por VARCHAR(100),

  total_eventos_relacionados INT DEFAULT 0,

  FOREIGN KEY (analise_id) REFERENCES monitor_analises(id) ON DELETE SET NULL,
  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,
  FOREIGN KEY (veiculomonitor_id) REFERENCES veiculomonitor(id) ON DELETE CASCADE,

  INDEX idx_status (status),
  INDEX idx_monitor (monitor_id),
  INDEX idx_criado (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
