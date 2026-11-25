-- UI-8.2: papéis e permissões explícitas por vínculo de tenant.
CREATE TABLE IF NOT EXISTS monitoramento.auth_permissions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  permission_key VARCHAR(100) NOT NULL,
  description VARCHAR(250) NOT NULL,
  PRIMARY KEY(id), UNIQUE KEY uq_auth_permission_key(permission_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_roles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  role_key VARCHAR(100) NOT NULL,
  name VARCHAR(150) NOT NULL,
  scope ENUM('tenant','platform') NOT NULL DEFAULT 'tenant',
  system_role BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY(id), UNIQUE KEY uq_auth_role_key(role_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_role_permissions (
  role_id BIGINT UNSIGNED NOT NULL,
  permission_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY(role_id,permission_id),
  CONSTRAINT fk_role_permission_role FOREIGN KEY(role_id) REFERENCES monitoramento.auth_roles(id) ON DELETE RESTRICT,
  CONSTRAINT fk_role_permission_permission FOREIGN KEY(permission_id) REFERENCES monitoramento.auth_permissions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS monitoramento.auth_membership_roles (
  membership_id BIGINT UNSIGNED NOT NULL,
  role_id BIGINT UNSIGNED NOT NULL,
  assigned_by BIGINT UNSIGNED NULL,
  assigned_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(membership_id,role_id),
  CONSTRAINT fk_membership_role_membership FOREIGN KEY(membership_id) REFERENCES monitoramento.auth_memberships(id) ON DELETE RESTRICT,
  CONSTRAINT fk_membership_role_role FOREIGN KEY(role_id) REFERENCES monitoramento.auth_roles(id) ON DELETE RESTRICT,
  CONSTRAINT fk_membership_role_assigner FOREIGN KEY(assigned_by) REFERENCES monitoramento.auth_users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO monitoramento.auth_permissions(permission_key,description) VALUES
('fleet.read','Consultar frota e contexto'),('telemetry.read','Consultar telemetria'),
('incident.read','Consultar incidentes'),('incident.operate','Atender incidentes'),
('incident.classify','Classificar incidentes'),('action.approve','Aprovar ações'),
('action.reprocess','Reprocessar ações'),('notification.operate','Operar notificações'),
('geofence.manage','Gerenciar cercas'),('route.manage','Gerenciar rotas'),
('monitor.manage','Gerenciar monitores'),('agent.configure','Configurar agentes'),
('detector.configure','Configurar detectores'),('report.read','Consultar relatórios'),
('report.export','Exportar relatórios'),('report.schedule','Agendar relatórios'),
('device.command.request','Solicitar comando'),('device.command.approve','Aprovar comando'),
('audit.read','Consultar auditoria'),('health.read','Consultar saúde detalhada'),
('tenant.manage','Administrar usuários do tenant'),('platform.admin','Administrar plataforma');

INSERT IGNORE INTO monitoramento.auth_roles(role_key,name,scope) VALUES
('viewer','Visualizador','tenant'),('operator','Operador','tenant'),
('supervisor','Supervisor','tenant'),('configurator','Configurador','tenant'),
('auditor','Auditor','tenant'),('tenant_admin','Administrador da empresa','tenant'),
('platform_admin','Administrador da plataforma','platform');

-- Visualizador.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r JOIN monitoramento.auth_permissions p
WHERE r.role_key='viewer' AND p.permission_key IN ('fleet.read','telemetry.read','incident.read','report.read');
-- Operador herda leitura e opera o atendimento.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r JOIN monitoramento.auth_permissions p
WHERE r.role_key='operator' AND p.permission_key IN ('fleet.read','telemetry.read','incident.read','report.read','incident.operate','notification.operate','device.command.request');
-- Supervisor opera, classifica e aprova.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r JOIN monitoramento.auth_permissions p
WHERE r.role_key='supervisor' AND p.permission_key IN ('fleet.read','telemetry.read','incident.read','report.read','incident.operate','incident.classify','notification.operate','action.approve','action.reprocess','report.export','device.command.request','device.command.approve');
-- Configurador gerencia regras, cercas, rotas e agentes.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r JOIN monitoramento.auth_permissions p
WHERE r.role_key='configurator' AND p.permission_key IN ('fleet.read','telemetry.read','incident.read','report.read','geofence.manage','route.manage','monitor.manage','agent.configure','detector.configure');
-- Auditor somente consulta evidências e saúde.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r JOIN monitoramento.auth_permissions p
WHERE r.role_key='auditor' AND p.permission_key IN ('fleet.read','incident.read','report.read','report.export','audit.read','health.read');
-- Administradores recebem todas as permissões do seu escopo; platform_admin também possui platform.admin.
INSERT IGNORE INTO monitoramento.auth_role_permissions(role_id,permission_id)
SELECT r.id,p.id FROM monitoramento.auth_roles r CROSS JOIN monitoramento.auth_permissions p
WHERE r.role_key IN ('tenant_admin','platform_admin')
  AND (r.role_key='platform_admin' OR p.permission_key<>'platform.admin');
