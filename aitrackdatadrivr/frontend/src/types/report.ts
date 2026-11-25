export type ReportMode = 'tracker' | 'dirijabem' | 'unified';

export interface BehaviorReport {
  schema_version: 'behavior-report.v1';
  public_id: string;
  definition: { key: string; version: number };
  formula_version: string;
  filters: { from: string; to: string; timezone: string; mode: ReportMode };
  generated_at: string;
  idempotent_replay: boolean;
  summary: {
    mode: ReportMode;
    sources: string[];
    event_count: number;
    distance_km: number;
    driving_seconds: number;
    coverage: number;
    events_per_100_km: number | null;
    events_per_driving_hour: number | null;
    source_breakdown: Record<string, { event_count: number; distance_km: number; driving_seconds: number; quality: string }>;
  };
}
