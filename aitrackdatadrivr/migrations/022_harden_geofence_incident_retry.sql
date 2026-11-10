-- UI-3.10: legado não entra na fila e deferimentos ganham retentativa espaçada.
ALTER TABLE monitoramento.geofence_events
  MODIFY correlation_status
    ENUM('pending','correlated','deferred','error','ignored')
    NOT NULL DEFAULT 'deferred',
  ADD COLUMN IF NOT EXISTS next_correlation_at DATETIME(6) NULL
    AFTER correlation_error;

UPDATE monitoramento.geofence_events
   SET correlation_status = 'deferred',
       correlation_error = 'legacy_event_without_episode',
       next_correlation_at = NULL
 WHERE violation_episode_id IS NULL
   AND correlation_status = 'pending';
