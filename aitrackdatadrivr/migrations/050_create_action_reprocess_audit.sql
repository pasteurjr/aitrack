-- UI-6.10: reprocessamento cria nova ação e preserva dead-letter original.
CREATE TABLE IF NOT EXISTS monitoramento.action_reprocess_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  original_action_id BIGINT UNSIGNED NOT NULL,
  replacement_action_id BIGINT UNSIGNED NOT NULL,
  actor_id VARCHAR(100) NOT NULL,
  reason VARCHAR(1000) NOT NULL,
  idempotency_key VARCHAR(150) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id), KEY idx_action_reprocess_original(original_action_id,created_at,id),
  UNIQUE KEY uq_action_reprocess_replacement(replacement_action_id),
  UNIQUE KEY uq_action_reprocess_key(idempotency_key),
  CONSTRAINT fk_action_reprocess_original FOREIGN KEY(original_action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT,
  CONSTRAINT fk_action_reprocess_replacement FOREIGN KEY(replacement_action_id)
    REFERENCES monitoramento.action_queue(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_reprocess_update BEFORE UPDATE ON monitoramento.action_reprocess_audit
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='reprocess audit is immutable'; END$$
CREATE OR REPLACE TRIGGER monitoramento.trg_action_reprocess_delete BEFORE DELETE ON monitoramento.action_reprocess_audit
FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='reprocess audit cannot be deleted'; END$$
DELIMITER ;
