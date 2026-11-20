-- UI-6.12: referência segura de transcrição e classificação estruturada.
CREATE TABLE IF NOT EXISTS monitoramento.voice_response_analyses (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  voice_receipt_id BIGINT UNSIGNED NOT NULL,
  action_id BIGINT UNSIGNED NOT NULL,
  provider_event_id VARCHAR(150) NOT NULL,
  audio_ref VARCHAR(300) NOT NULL,
  audio_sha256 CHAR(64) NOT NULL,
  audio_authorized BOOLEAN NOT NULL,
  authorization_source VARCHAR(100) NOT NULL,
  transcript_ref VARCHAR(300) NOT NULL,
  transcript_sha256 CHAR(64) NOT NULL,
  model_code VARCHAR(100) NOT NULL,
  model_version VARCHAR(100) NOT NULL,
  classification ENUM('owner_confirmed','owner_denied','no_answer','unclear','emergency','opt_out') NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  review_status ENUM('not_required','pending','approved','corrected') NOT NULL,
  structured_result_json LONGTEXT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), UNIQUE KEY uq_voice_response_event(provider_event_id),
  KEY idx_voice_response_action(action_id,created_at,id),
  CONSTRAINT fk_voice_response_receipt FOREIGN KEY(voice_receipt_id)
    REFERENCES monitoramento.voice_dispatch_receipts(id) ON DELETE RESTRICT,
  CONSTRAINT fk_voice_response_action FOREIGN KEY(action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT chk_voice_response_authorized CHECK(audio_authorized=TRUE),
  CONSTRAINT chk_voice_response_confidence CHECK(confidence BETWEEN 0 AND 1),
  CONSTRAINT chk_voice_response_result CHECK(JSON_VALID(structured_result_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_voice_response_update BEFORE UPDATE ON monitoramento.voice_response_analyses
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='voice response analysis is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_voice_response_delete BEFORE DELETE ON monitoramento.voice_response_analyses
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='voice response analyses cannot be deleted'; END$$
DELIMITER ;
