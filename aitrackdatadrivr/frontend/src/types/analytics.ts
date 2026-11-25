export type AnalyticsSource = 'tracker' | 'dirijabem';

export interface AnalyticsSlice {
  period: { from: string; to: string; timezone: string; duration_seconds: number; interval: '[from,to)' };
  sources: AnalyticsSource[];
  total_events: number;
  source_totals: Record<AnalyticsSource, number>;
  by_type: { source: AnalyticsSource; event_type: string; total: number }[];
  by_vehicle: { source: AnalyticsSource; device_id: string | null; total: number }[];
}

export interface BehaviorAnalyticsResponse {
  schema_version: 'behavior-analytics.v1';
  formula_version: 'event-count.v1';
  current: AnalyticsSlice;
  comparison: AnalyticsSlice | null;
}
