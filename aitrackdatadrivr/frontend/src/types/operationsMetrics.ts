interface DurationMetric { valid_count: number; excluded_count: number; median_seconds: number | null; p95_seconds: number | null }

export interface OperationsMetrics {
  schema_version: 'operations-metrics.v1';
  incident_count: number;
  detection: DurationMetric;
  triage: DurationMetric;
  resolution: DurationMetric;
  sla: { within: number; at_risk: number; breached: number; excluded: number; valid_count: number };
  automation: { automated_incidents: number; denominator: number; rate: number | null; simulated_actions: number; externally_sent_actions: number };
  human_intervention: { incidents: number; denominator: number; rate: number | null };
  action_failures: { transient_failed: number; dead_letter: number };
}
