-- UI-2.8: classificação auditável de acertos e falhas de detecção.
ALTER TABLE tracker.incidents
  ADD COLUMN IF NOT EXISTS detection_outcome
    ENUM('unreviewed', 'true_positive', 'false_positive', 'false_negative')
    NOT NULL DEFAULT 'unreviewed' AFTER false_positive,
  ADD COLUMN IF NOT EXISTS classification_reason VARCHAR(50) NULL AFTER detection_outcome,
  ADD COLUMN IF NOT EXISTS classified_by VARCHAR(100) NULL AFTER classification_reason,
  ADD COLUMN IF NOT EXISTS classified_at DATETIME(6) NULL AFTER classified_by;

ALTER TABLE tracker.incidents
  ADD INDEX IF NOT EXISTS idx_incidents_detection_outcome
    (detection_outcome, classified_at);
