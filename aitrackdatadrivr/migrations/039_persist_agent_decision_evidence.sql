-- UI-5.10: proveniência consultável da decisão, sem raciocínio livre.

ALTER TABLE monitoramento.agent_run_decisions
  ADD COLUMN classification VARCHAR(50) NULL AFTER authorization_json,
  ADD COLUMN confidence DECIMAL(6,5) NULL AFTER classification,
  ADD COLUMN risk_level VARCHAR(20) NULL AFTER confidence,
  ADD COLUMN risk_score DECIMAL(6,2) NULL AFTER risk_level,
  ADD COLUMN context_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL
    AFTER risk_score,
  ADD COLUMN evidence_manifest_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL
    AFTER context_sha256,
  ADD COLUMN evidence_count SMALLINT UNSIGNED NULL AFTER evidence_manifest_sha256,
  ADD KEY idx_agent_decision_classification (classification,risk_level,confidence);

CREATE TABLE IF NOT EXISTS monitoramento.agent_decision_evidence (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  decision_id BIGINT UNSIGNED NOT NULL,
  ordinal SMALLINT UNSIGNED NOT NULL,
  source_code VARCHAR(30) NOT NULL,
  evidence_type VARCHAR(50) NOT NULL,
  evidence_ref VARCHAR(150) NOT NULL,
  summary VARCHAR(500) NOT NULL,
  observed_at DATETIME(6) NULL,
  content_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_decision_evidence_ordinal (decision_id,ordinal),
  KEY idx_agent_decision_evidence_ref (source_code,evidence_type,evidence_ref),
  CONSTRAINT fk_agent_decision_evidence_decision FOREIGN KEY (decision_id)
    REFERENCES monitoramento.agent_run_decisions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$
CREATE TRIGGER monitoramento.trg_agent_evidence_immutable_update
BEFORE UPDATE ON monitoramento.agent_decision_evidence
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent decision evidence is immutable';
END$$

CREATE TRIGGER monitoramento.trg_agent_evidence_immutable_delete
BEFORE DELETE ON monitoramento.agent_decision_evidence
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='agent decision evidence cannot be deleted';
END$$
DELIMITER ;
