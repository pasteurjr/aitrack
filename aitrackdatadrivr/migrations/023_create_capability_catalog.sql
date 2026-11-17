-- UI-4.1: catálogo versionado das capacidades efetivamente disponíveis.
-- Perfis são imutáveis por (protocolo, modelo, versão). Nova evidência cria
-- nova versão; não se reescreve a interpretação histórica.

CREATE TABLE IF NOT EXISTS monitoramento.capability_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  protocol_code VARCHAR(50) NOT NULL,
  device_model VARCHAR(100) NOT NULL DEFAULT '*',
  version_number INT UNSIGNED NOT NULL,
  status ENUM('draft','active','superseded') NOT NULL DEFAULT 'draft',
  evidence_source VARCHAR(255) NOT NULL,
  notes TEXT NULL,
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_capability_profile_version
    (protocol_code, device_model, version_number),
  KEY idx_capability_profile_active
    (protocol_code, device_model, status, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.capability_profile_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  profile_id BIGINT UNSIGNED NOT NULL,
  capability_code VARCHAR(100) NOT NULL,
  capability_type ENUM('sensor','command','derived') NOT NULL,
  support_status ENUM('confirmed','unavailable','unknown') NOT NULL,
  normalized_field VARCHAR(100) NULL,
  value_type ENUM('boolean','number','string','geo','command') NOT NULL,
  unit VARCHAR(30) NULL,
  evidence TEXT NOT NULL,
  constraints_json LONGTEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_capability_profile_item (profile_id, capability_code),
  CONSTRAINT fk_capability_item_profile FOREIGN KEY (profile_id)
    REFERENCES monitoramento.capability_profiles(id) ON DELETE RESTRICT,
  CONSTRAINT chk_capability_constraints_json CHECK
    (constraints_json IS NULL OR JSON_VALID(constraints_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.capability_profiles
  (protocol_code, device_model, version_number, status, evidence_source, notes, created_by)
VALUES
  ('maxtrack', '*', 1, 'active', 'MATRIZ_CAMPOS_PROTOCOLOS_TRACKER.md + protocol_parsers.py',
   'REV01 implementado; identidade apenas por prefixo controlado.', 'codex-ui-4.1'),
  ('suntech', '*', 1, 'active', 'MATRIZ_CAMPOS_PROTOCOLOS_TRACKER.md + protocol_parsers.py',
   'Formato ST310U implementado; status GPS atual é fixo e não medido.', 'codex-ui-4.1'),
  ('queclink', '*', 1, 'active', 'MATRIZ_CAMPOS_PROTOCOLOS_TRACKER.md + protocol_parsers.py',
   'Somente mensagem GTRIC implementada; alarmes +RESP adicionais não são aceitos.', 'codex-ui-4.1');

-- Capacidades comuns realmente extraídas dos três formatos atuais.
INSERT IGNORE INTO monitoramento.capability_profile_items
  (profile_id, capability_code, capability_type, support_status,
   normalized_field, value_type, unit, evidence, constraints_json)
SELECT p.id, common.capability_code, 'sensor', 'confirmed',
       common.normalized_field, common.value_type, common.unit,
       common.evidence, common.constraints_json
  FROM monitoramento.capability_profiles p
  JOIN (
    SELECT 'position' capability_code, 'latitude/longitude' normalized_field,
           'geo' value_type, NULL unit, 'Extraído do pacote pelo parser ativo.' evidence,
           '{"required":true}' constraints_json
    UNION ALL SELECT 'speed', 'speed', 'number', 'km/h', 'Extraído do pacote pelo parser ativo.', NULL
    UNION ALL SELECT 'heading', 'heading', 'number', 'degree', 'Extraído do pacote pelo parser ativo.', '{"min":0,"max":359}'
    UNION ALL SELECT 'ignition', 'ignition', 'boolean', NULL, 'Extraído pelo parser; ainda não persistido no pipeline.', NULL
    UNION ALL SELECT 'external_voltage', 'battery_voltage', 'number', 'V', 'Extraído pelo parser; ainda não persistido no pipeline.', NULL
    UNION ALL SELECT 'observed_at', 'timestamp', 'string', 'ISO-8601', 'Extraído do relógio informado no pacote.', NULL
  ) common
 WHERE p.version_number = 1 AND p.status = 'active';

-- Diferenças comprovadas por protocolo.
INSERT IGNORE INTO monitoramento.capability_profile_items
  (profile_id, capability_code, capability_type, support_status,
   normalized_field, value_type, unit, evidence, constraints_json)
SELECT id, 'gps_valid', 'sensor', 'confirmed', 'gps_status', 'boolean', NULL,
       'Maxtrack REV01 lê status A do pacote.', NULL
  FROM monitoramento.capability_profiles WHERE protocol_code='maxtrack' AND version_number=1;
INSERT IGNORE INTO monitoramento.capability_profile_items
  (profile_id, capability_code, capability_type, support_status,
   normalized_field, value_type, unit, evidence, constraints_json)
SELECT id, 'gps_valid', 'sensor', 'unavailable', 'gps_status', 'boolean', NULL,
       'Parser atual fixa True; não representa medição do equipamento.', NULL
  FROM monitoramento.capability_profiles WHERE protocol_code IN ('suntech','queclink') AND version_number=1;
INSERT IGNORE INTO monitoramento.capability_profile_items
  (profile_id, capability_code, capability_type, support_status,
   normalized_field, value_type, unit, evidence, constraints_json)
SELECT id, 'altitude', 'sensor',
       IF(protocol_code='queclink','confirmed','unavailable'),
       'altitude', 'number', 'm',
       IF(protocol_code='queclink','Extraído da mensagem GTRIC.','Parser retorna None.'), NULL
  FROM monitoramento.capability_profiles WHERE version_number=1;

-- Sinais e comandos não comprovados nunca são anunciados como disponíveis.
INSERT IGNORE INTO monitoramento.capability_profile_items
  (profile_id, capability_code, capability_type, support_status,
   normalized_field, value_type, unit, evidence, constraints_json)
SELECT p.id, unsupported.capability_code, unsupported.capability_type,
       unsupported.support_status, unsupported.normalized_field,
       unsupported.value_type, NULL, unsupported.evidence, NULL
  FROM monitoramento.capability_profiles p
  JOIN (
    SELECT 'panic_signal' capability_code, 'sensor' capability_type,
           'unavailable' support_status, 'panic' normalized_field,
           'boolean' value_type,
           'Parser atual fixa False; nenhuma mensagem SOS/pânico é reconhecida.' evidence
    UNION ALL SELECT 'tamper_signal','sensor','unavailable',NULL,'boolean',
           'Nenhuma mensagem tamper é reconhecida pelo parser atual.'
    UNION ALL SELECT 'remote_immobilization','command','unknown',NULL,'command',
           'Não existe canal de comando nem ACK/NACK implementado.'
    UNION ALL SELECT 'buzzer_activation','command','unknown',NULL,'command',
           'Não existe canal de comando nem ACK/NACK implementado.'
  ) unsupported;
