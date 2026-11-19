-- UI-6.2: identidade e estados finais da fila não podem ser reescritos.
DELIMITER $$
CREATE TRIGGER monitoramento.trg_action_queue_guard_update
BEFORE UPDATE ON monitoramento.action_queue
FOR EACH ROW BEGIN
  IF NOT (OLD.public_id <=> NEW.public_id)
     OR NOT (OLD.incident_id <=> NEW.incident_id)
     OR NOT (OLD.agent_run_id <=> NEW.agent_run_id)
     OR NOT (OLD.decision_id <=> NEW.decision_id)
     OR NOT (OLD.action_index <=> NEW.action_index)
     OR NOT (OLD.action_type <=> NEW.action_type)
     OR NOT (OLD.target_type <=> NEW.target_type)
     OR NOT (OLD.target_ref <=> NEW.target_ref)
     OR NOT (OLD.payload_json <=> NEW.payload_json)
     OR NOT (OLD.policy_snapshot_json <=> NEW.policy_snapshot_json)
     OR NOT (OLD.idempotency_key <=> NEW.idempotency_key)
     OR NOT (OLD.correlation_id <=> NEW.correlation_id)
     OR NOT (OLD.causation_id <=> NEW.causation_id)
     OR OLD.status IN ('responded','dead','cancelled','simulated') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='action identity/final state is immutable';
  END IF;
END$$
CREATE TRIGGER monitoramento.trg_action_queue_guard_delete
BEFORE DELETE ON monitoramento.action_queue
FOR EACH ROW BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='actions cannot be deleted';
END$$
DELIMITER ;
