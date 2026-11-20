-- UI-6.6: templates estáveis com versões imutáveis e aprovação explícita.
CREATE TABLE IF NOT EXISTS monitoramento.message_templates (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  template_key VARCHAR(100) NOT NULL,
  name VARCHAR(150) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_message_template_key(template_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.message_template_versions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  template_id BIGINT UNSIGNED NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  locale VARCHAR(15) NOT NULL,
  channel ENUM('sms','whatsapp','push','generic') NOT NULL,
  body TEXT NOT NULL,
  variable_schema_json LONGTEXT NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  status ENUM('draft','approved','superseded') NOT NULL DEFAULT 'draft',
  created_by VARCHAR(100) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  approved_by VARCHAR(100) NULL,
  approved_at DATETIME(6) NULL,
  approved_template_id BIGINT UNSIGNED AS
    (CASE WHEN status='approved' THEN template_id ELSE NULL END) PERSISTENT,
  PRIMARY KEY(id),
  UNIQUE KEY uq_message_template_version(template_id,version_no),
  UNIQUE KEY uq_message_template_approved(approved_template_id),
  CONSTRAINT fk_message_template_version_template FOREIGN KEY(template_id)
    REFERENCES monitoramento.message_templates(id) ON DELETE RESTRICT,
  CONSTRAINT chk_message_template_schema CHECK(JSON_VALID(variable_schema_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_message_template_version_guard
BEFORE UPDATE ON monitoramento.message_template_versions FOR EACH ROW BEGIN
  IF NOT (OLD.template_id <=> NEW.template_id)
     OR NOT (OLD.version_no <=> NEW.version_no) OR NOT (OLD.locale <=> NEW.locale)
     OR NOT (OLD.channel <=> NEW.channel) OR NOT (OLD.body <=> NEW.body)
     OR NOT (OLD.variable_schema_json <=> NEW.variable_schema_json)
     OR NOT (OLD.content_sha256 <=> NEW.content_sha256)
     OR NOT (OLD.created_by <=> NEW.created_by) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='template version content is immutable';
  END IF;
  IF NOT ((OLD.status='draft' AND NEW.status='approved')
       OR (OLD.status='approved' AND NEW.status='superseded')) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='invalid template status transition';
  END IF;
END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_message_template_version_delete
BEFORE DELETE ON monitoramento.message_template_versions FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='template versions cannot be deleted';
END$$
DELIMITER ;
