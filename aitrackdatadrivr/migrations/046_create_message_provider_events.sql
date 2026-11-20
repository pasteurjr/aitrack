-- UI-6.5: eventos assíncronos normalizados de entrega, leitura e resposta.
CREATE TABLE IF NOT EXISTS monitoramento.message_provider_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  action_id BIGINT UNSIGNED NOT NULL,
  receipt_id BIGINT UNSIGNED NOT NULL,
  provider_code VARCHAR(50) NOT NULL,
  provider_event_id VARCHAR(150) NOT NULL,
  normalized_status ENUM('accepted','sent','delivered','read','responded','failed','unknown') NOT NULL,
  provider_status VARCHAR(100) NOT NULL,
  provider_occurred_at DATETIME(6) NULL,
  received_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  payload_sha256 CHAR(64) NOT NULL,
  sanitized_metadata_json LONGTEXT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_message_provider_event (provider_code,provider_event_id),
  KEY idx_message_provider_timeline (action_id,provider_occurred_at,received_at,id),
  CONSTRAINT fk_message_provider_event_action FOREIGN KEY(action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT fk_message_provider_event_receipt FOREIGN KEY(receipt_id)
    REFERENCES monitoramento.message_dispatch_receipts(id) ON DELETE RESTRICT,
  CONSTRAINT chk_message_provider_metadata CHECK(JSON_VALID(sanitized_metadata_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_message_provider_event_update
BEFORE UPDATE ON monitoramento.message_provider_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='provider events are immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_message_provider_event_delete
BEFORE DELETE ON monitoramento.message_provider_events
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='provider events cannot be deleted'; END$$
DELIMITER ;
