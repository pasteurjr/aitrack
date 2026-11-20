-- UI-6.11: recibos imutáveis de chamadas exclusivamente em sandbox.
CREATE TABLE IF NOT EXISTS monitoramento.voice_dispatch_receipts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  action_id BIGINT UNSIGNED NOT NULL,
  script_version_id BIGINT UNSIGNED NOT NULL,
  provider_code VARCHAR(50) NOT NULL,
  provider_call_id VARCHAR(150) NOT NULL,
  destination_hash CHAR(64) NOT NULL,
  script_sha256 CHAR(64) NOT NULL,
  request_sha256 CHAR(64) NOT NULL,
  automation_disclosed BOOLEAN NOT NULL,
  http_status SMALLINT UNSIGNED NOT NULL,
  response_json LONGTEXT NOT NULL,
  dispatched_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_voice_receipt_action(action_id),
  UNIQUE KEY uq_voice_receipt_provider(provider_code,provider_call_id),
  CONSTRAINT fk_voice_receipt_action FOREIGN KEY(action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT fk_voice_receipt_script FOREIGN KEY(script_version_id)
    REFERENCES monitoramento.message_template_versions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_voice_receipt_response CHECK(JSON_VALID(response_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_voice_receipt_update BEFORE UPDATE ON monitoramento.voice_dispatch_receipts
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='voice receipt is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_voice_receipt_delete BEFORE DELETE ON monitoramento.voice_dispatch_receipts
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='voice receipts cannot be deleted'; END$$
DELIMITER ;
