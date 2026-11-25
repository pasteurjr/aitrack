export type IntegrationHealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

export interface IntegrationHealthItem {
  key?: string;
  component_key?: string;
  id?: string;
  name?: string;
  label?: string;
  display_name?: string;
  status?: string;
  message?: string;
  detail?: string;
  reason_sanitized?: string;
  checked_at?: string;
  heartbeat_at?: string;
  last_success_at?: string;
  latency_ms?: number;
}

export type IntegrationHealthCollection =
  | IntegrationHealthItem[]
  | Record<string, IntegrationHealthItem | string>;

export interface IntegrationHealthResponse {
  generated_at?: string;
  checked_at?: string;
  overall_status?: string;
  status?: string;
  integrations?: IntegrationHealthCollection;
  components?: IntegrationHealthCollection;
  active_alerts?: Array<{
    alert_key: string;
    component_key: string;
    severity: 'warning' | 'high' | 'critical';
    summary: string;
  }>;
  data?: {
    integrations?: IntegrationHealthCollection;
    components?: IntegrationHealthCollection;
  };
}
