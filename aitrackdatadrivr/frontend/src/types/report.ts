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

export interface ReportExport {
  schema_version: 'report-export.v1';
  public_id: string;
  status: 'completed' | 'failed';
  format: 'csv' | 'json';
  artifact_sha256: string;
  artifact_size_bytes: number;
  row_count: number;
  content: string;
  delivery: 'internal_download';
}

export interface ReportExportSchedule {
  schema_version: 'report-export-schedule.v1';
  public_id: string;
  status: 'blocked_auth';
  next_run_at: null;
  calculated_next_run_at: string;
  block_reason: 'AUTH_AND_RBAC_REQUIRED';
}
