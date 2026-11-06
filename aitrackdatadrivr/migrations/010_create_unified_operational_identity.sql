-- UI-3.0A: camada operacional comum ao Tracker e ao Dirija Bem.
-- Esta migration somente cria estruturas; o backfill será feito separadamente.
CREATE DATABASE IF NOT EXISTS monitoramento
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.fontes_dados (
  codigo VARCHAR(30) NOT NULL,
  nome VARCHAR(100) NOT NULL,
  categoria ENUM('telemetria', 'comportamento', 'operacional') NOT NULL,
  somente_leitura BOOLEAN NOT NULL DEFAULT TRUE,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO monitoramento.fontes_dados
    (codigo, nome, categoria, somente_leitura)
VALUES
    ('tracker', 'Tracker / AITrack', 'telemetria', TRUE),
    ('dirijabem', 'Dirija Bem', 'comportamento', TRUE)
ON DUPLICATE KEY UPDATE
    nome = VALUES(nome),
    categoria = VALUES(categoria),
    somente_leitura = VALUES(somente_leitura);

CREATE TABLE IF NOT EXISTS monitoramento.veiculos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  placa VARCHAR(20) NULL,
  descricao VARCHAR(200) NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  merged_into_id BIGINT UNSIGNED NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_veiculos_public_id (public_id),
  KEY idx_veiculos_placa (placa, ativo),
  KEY idx_veiculos_merge (merged_into_id),
  CONSTRAINT fk_veiculos_merge
    FOREIGN KEY (merged_into_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.veiculo_identidades (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  fonte_codigo VARCHAR(30) NOT NULL,
  tipo_identidade ENUM('vehicle_id', 'device_id', 'plate') NOT NULL,
  valor_externo VARCHAR(150) NOT NULL,
  principal BOOLEAN NOT NULL DEFAULT FALSE,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  primeiro_visto_em DATETIME(6) NULL,
  ultimo_visto_em DATETIME(6) NULL,
  atributos JSON NULL,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_veiculo_identidade_origem
    (fonte_codigo, tipo_identidade, valor_externo),
  KEY idx_veiculo_identidades_vehicle (vehicle_id, ativo),
  CONSTRAINT fk_veiculo_identidades_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_veiculo_identidades_fonte
    FOREIGN KEY (fonte_codigo) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.motoristas (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  nome VARCHAR(200) NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_motoristas_public_id (public_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.motorista_identidades (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  driver_id BIGINT UNSIGNED NOT NULL,
  fonte_codigo VARCHAR(30) NOT NULL,
  tipo_identidade ENUM('driver_id', 'user_id', 'document') NOT NULL,
  valor_externo VARCHAR(150) NOT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  atributos JSON NULL,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  atualizado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_motorista_identidade_origem
    (fonte_codigo, tipo_identidade, valor_externo),
  KEY idx_motorista_identidades_driver (driver_id, ativo),
  CONSTRAINT fk_motorista_identidades_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_motorista_identidades_fonte
    FOREIGN KEY (fonte_codigo) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.veiculo_motorista_vinculos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vehicle_id BIGINT UNSIGNED NOT NULL,
  driver_id BIGINT UNSIGNED NOT NULL,
  fonte_codigo VARCHAR(30) NULL,
  valido_desde DATETIME(6) NOT NULL,
  valido_ate DATETIME(6) NULL,
  criado_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_vinculos_vehicle_periodo (vehicle_id, valido_desde, valido_ate),
  KEY idx_vinculos_driver_periodo (driver_id, valido_desde, valido_ate),
  CONSTRAINT fk_vinculos_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES monitoramento.veiculos(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_vinculos_driver
    FOREIGN KEY (driver_id) REFERENCES monitoramento.motoristas(id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_vinculos_fonte
    FOREIGN KEY (fonte_codigo) REFERENCES monitoramento.fontes_dados(codigo)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
