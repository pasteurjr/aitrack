-- UI-5.3: decisões persistidas somente após validação do contrato v1.

ALTER TABLE monitoramento.agent_run_decisions
  ADD COLUMN decision_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL
    AFTER decision_json,
  ADD COLUMN validated_at DATETIME(6) NULL AFTER decision_sha256,
  ADD KEY idx_agent_decision_hash (decision_sha256);

-- Não há decisões anteriores no ambiente atual. A nulabilidade preserva uma
-- migração aditiva caso outro ambiente já tenha histórico unstructured.v1.
