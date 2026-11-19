-- UI-6.3: projeção persistente da primeira ferramenta de ação.
CREATE TABLE IF NOT EXISTS monitoramento.internal_notifications (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  action_id BIGINT UNSIGNED NOT NULL,
  incident_id BIGINT UNSIGNED NOT NULL,
  recipient_ref VARCHAR(150) NOT NULL,
  title VARCHAR(200) NOT NULL,
  body TEXT NOT NULL,
  priority ENUM('low','normal','high','urgent') NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  read_at DATETIME(6) NULL,
  read_by VARCHAR(100) NULL,
  read_idempotency_key VARCHAR(150) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_internal_notification_public (public_id),
  UNIQUE KEY uq_internal_notification_action (action_id),
  UNIQUE KEY uq_internal_notification_read (read_idempotency_key),
  KEY idx_internal_notification_inbox (recipient_ref,read_at,created_at,id),
  CONSTRAINT fk_internal_notification_action FOREIGN KEY (action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT fk_internal_notification_incident FOREIGN KEY (incident_id)
    REFERENCES monitoramento.incidents(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_internal_notification_guard
BEFORE UPDATE ON monitoramento.internal_notifications
FOR EACH ROW BEGIN
  IF NOT (OLD.public_id <=> NEW.public_id) OR NOT (OLD.action_id <=> NEW.action_id)
     OR NOT (OLD.incident_id <=> NEW.incident_id)
     OR NOT (OLD.recipient_ref <=> NEW.recipient_ref)
     OR NOT (OLD.title <=> NEW.title) OR NOT (OLD.body <=> NEW.body)
     OR NOT (OLD.priority <=> NEW.priority) OR OLD.read_at IS NOT NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='notification identity/read state is immutable';
  END IF;
END$$
CREATE TRIGGER monitoramento.trg_internal_notification_delete
BEFORE DELETE ON monitoramento.internal_notifications
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='notifications cannot be deleted';
END$$
DELIMITER ;
