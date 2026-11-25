-- UI-7.3: estado persistente e episódios de desvio/parada.
CREATE TABLE IF NOT EXISTS monitoramento.route_planned_stops (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,route_version_id BIGINT UNSIGNED NOT NULL,stop_order SMALLINT UNSIGNED NOT NULL,
 name VARCHAR(150) NOT NULL,longitude DOUBLE NOT NULL,latitude DOUBLE NOT NULL,radius_meters DECIMAL(10,2) NOT NULL,dwell_seconds INT UNSIGNED NOT NULL,
 PRIMARY KEY(id),UNIQUE KEY uq_route_stop(route_version_id,stop_order),
 CONSTRAINT fk_route_stop_version FOREIGN KEY(route_version_id) REFERENCES monitoramento.route_versions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS monitoramento.route_execution_states (
 execution_id BIGINT UNSIGNED NOT NULL,stable_on_route BOOLEAN NULL,pending_on_route BOOLEAN NULL,pending_samples SMALLINT UNSIGNED NOT NULL DEFAULT 0,
 last_distance_meters DECIMAL(12,2) NULL,last_observed_at DATETIME(6) NULL,stop_started_at DATETIME(6) NULL,last_speed_kmh DECIMAL(8,2) NULL,version INT UNSIGNED NOT NULL DEFAULT 1,
 PRIMARY KEY(execution_id),CONSTRAINT fk_route_state_execution FOREIGN KEY(execution_id) REFERENCES monitoramento.route_executions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS monitoramento.route_episodes (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,public_id CHAR(36) NOT NULL,execution_id BIGINT UNSIGNED NOT NULL,
 episode_type ENUM('deviation','unplanned_stop') NOT NULL,status ENUM('active','recovered') NOT NULL,
 started_at DATETIME(6) NOT NULL,ended_at DATETIME(6) NULL,max_distance_meters DECIMAL(12,2) NULL,evidence_json LONGTEXT NOT NULL,
 active_key VARCHAR(100) AS (CASE WHEN status='active' THEN CONCAT(execution_id,':',episode_type) ELSE NULL END) PERSISTENT,
 PRIMARY KEY(id),UNIQUE KEY uq_route_episode_public(public_id),UNIQUE KEY uq_route_episode_active(active_key),KEY idx_route_episode_execution(execution_id,started_at,id),
 CONSTRAINT fk_route_episode_execution FOREIGN KEY(execution_id) REFERENCES monitoramento.route_executions(id) ON DELETE RESTRICT,
 CONSTRAINT chk_route_episode_evidence CHECK(JSON_VALID(evidence_json))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS monitoramento.route_position_receipts (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,execution_id BIGINT UNSIGNED NOT NULL,source VARCHAR(30) NOT NULL,external_position_id VARCHAR(100) NOT NULL,
 observed_at DATETIME(6) NOT NULL,distance_meters DECIMAL(12,2) NOT NULL,processed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 PRIMARY KEY(id),UNIQUE KEY uq_route_position(execution_id,source,external_position_id),
 CONSTRAINT fk_route_receipt_execution FOREIGN KEY(execution_id) REFERENCES monitoramento.route_executions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
