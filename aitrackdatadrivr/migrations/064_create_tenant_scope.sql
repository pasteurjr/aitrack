-- UI-8.3: propriedade explícita das raízes operacionais.
INSERT INTO monitoramento.tenants(public_id, slug, name, status)
SELECT '00000000-0000-0000-0000-000000000001', 'migration-default',
       'Dados migrados', 'active'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM monitoramento.tenants);

ALTER TABLE monitoramento.incidents ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE monitoramento.geofences ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE monitoramento.routes ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE monitoramento.agent_definitions ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE monitoramento.report_definitions ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE monitoramento.report_runs ADD COLUMN IF NOT EXISTS tenant_id BIGINT UNSIGNED NULL;

SET @migration_tenant_id := (
  SELECT id FROM monitoramento.tenants
  ORDER BY (slug='default') DESC, id ASC LIMIT 1
);
UPDATE monitoramento.incidents SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;
UPDATE monitoramento.geofences SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;
UPDATE monitoramento.routes SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;
UPDATE monitoramento.agent_definitions SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;
UPDATE monitoramento.report_definitions SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;
UPDATE monitoramento.report_runs SET tenant_id=@migration_tenant_id WHERE tenant_id IS NULL;

ALTER TABLE monitoramento.incidents MODIFY tenant_id BIGINT UNSIGNED NOT NULL;
ALTER TABLE monitoramento.geofences MODIFY tenant_id BIGINT UNSIGNED NOT NULL;
ALTER TABLE monitoramento.routes MODIFY tenant_id BIGINT UNSIGNED NOT NULL;
ALTER TABLE monitoramento.agent_definitions MODIFY tenant_id BIGINT UNSIGNED NOT NULL;
ALTER TABLE monitoramento.report_definitions MODIFY tenant_id BIGINT UNSIGNED NOT NULL;
ALTER TABLE monitoramento.report_runs MODIFY tenant_id BIGINT UNSIGNED NOT NULL;

CREATE INDEX IF NOT EXISTS idx_incidents_tenant ON monitoramento.incidents(tenant_id, updated_at, id);
CREATE INDEX IF NOT EXISTS idx_geofences_tenant ON monitoramento.geofences(tenant_id, atualizado_em, id);
CREATE INDEX IF NOT EXISTS idx_routes_tenant ON monitoramento.routes(tenant_id, updated_at, id);
CREATE INDEX IF NOT EXISTS idx_agents_tenant ON monitoramento.agent_definitions(tenant_id, lifecycle_status, id);
CREATE INDEX IF NOT EXISTS idx_report_def_tenant ON monitoramento.report_definitions(tenant_id, report_key, version_no);
CREATE INDEX IF NOT EXISTS idx_report_runs_tenant ON monitoramento.report_runs(tenant_id, generated_at, id);

CREATE TABLE IF NOT EXISTS monitoramento.tenant_source_bindings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  source_code ENUM('tracker','dirijabem') NOT NULL,
  external_type VARCHAR(50) NOT NULL,
  external_value VARCHAR(150) NOT NULL,
  status ENUM('active','quarantined','disabled') NOT NULL DEFAULT 'active',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(id),
  UNIQUE KEY uq_tenant_source_external(source_code, external_type, external_value),
  KEY idx_tenant_source(tenant_id, source_code, status),
  CONSTRAINT fk_tenant_source_tenant FOREIGN KEY(tenant_id)
    REFERENCES monitoramento.tenants(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
