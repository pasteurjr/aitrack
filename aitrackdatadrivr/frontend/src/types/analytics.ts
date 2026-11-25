export type AnalyticsSource = 'tracker' | 'dirijabem';

export interface AnalyticsSlice {
  period: { from: string; to: string; timezone: string; duration_seconds: number; interval: '[from,to)' };
  sources: AnalyticsSource[];
  total_events: number;
  source_totals: Record<AnalyticsSource, number>;
  by_type: { source: AnalyticsSource; event_type: string; total: number }[];
  normalized_by_type: { source: AnalyticsSource; event_type: string; total: number; events_per_100_km: number | null; events_per_driving_hour: number | null }[];
  by_vehicle: { source: AnalyticsSource; device_id: string | null; total: number }[];
  exposure: Record<AnalyticsSource, { distance_km: number; driving_seconds: number; valid_points: number; discarded_points: number; coverage: number; quality: 'complete' | 'partial' | 'unavailable'; bucket_count: number; formula_version: string }>;
  exposure_formula_version: string;
}

export interface BehaviorAnalyticsResponse {
  schema_version: 'behavior-analytics.v1';
  formula_version: 'event-count.v1';
  current: AnalyticsSlice;
  comparison: AnalyticsSlice | null;
}
