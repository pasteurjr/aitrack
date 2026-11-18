-- UI-5.6: recibos de ferramentas de leitura usadas pelos agentes.

CREATE TABLE IF NOT EXISTS monitoramento.agent_tool_invocations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  public_id CHAR(36) NOT NULL,
  run_id BIGINT UNSIGNED NULL,
  agent_id BIGINT UNSIGNED NOT NULL,
  tool_name VARCHAR(100) NOT NULL,
  arguments_json LONGTEXT NOT NULL,
  scope_json LONGTEXT NOT NULL,
  status ENUM('succeeded','denied','failed') NOT NULL,
  result_summary_json LONGTEXT NULL,
  arguments_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  result_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  correlation_id VARCHAR(100) NOT NULL,
  error_code VARCHAR(100) NULL,
  latency_ms INT UNSIGNED NOT NULL,
  invoked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_agent_tool_public (public_id),
  KEY idx_agent_tool_run (run_id,invoked_at,id),
  KEY idx_agent_tool_agent (agent_id,invoked_at,id),
  KEY idx_agent_tool_correlation (correlation_id,id),
  CONSTRAINT fk_agent_tool_run FOREIGN KEY (run_id)
    REFERENCES monitoramento.agent_runs(id) ON DELETE RESTRICT,
  CONSTRAINT fk_agent_tool_agent FOREIGN KEY (agent_id)
    REFERENCES monitoramento.agent_definitions(id) ON DELETE RESTRICT,
  CONSTRAINT chk_agent_tool_arguments CHECK (JSON_VALID(arguments_json)),
  CONSTRAINT chk_agent_tool_scope CHECK (JSON_VALID(scope_json)),
  CONSTRAINT chk_agent_tool_result CHECK
    (result_summary_json IS NULL OR JSON_VALID(result_summary_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
