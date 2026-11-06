export type IncidentStatus =
  | 'new'
  | 'triage'
  | 'in_progress'
  | 'waiting_response'
  | 'escalated'
  | 'resolved'
  | 'closed';

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';
export type IncidentSource = 'tracker' | 'dirijabem' | 'fused' | 'system';

export interface IncidentSummary {
  id: number;
  vehicle_id: number;
  device_id: string | null;
  codusu: number | null;
  placa: string | null;
  vehicle_name: string | null;
  monitor_id: number | null;
  monitor_name: string | null;
  incident_type: string;
  title: string;
  summary: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  risk_score: number | null;
  primary_source: IncidentSource;
  assigned_type: 'human' | 'agent' | null;
  assigned_to: string | null;
  latitude: number | null;
  longitude: number | null;
  event_count: number;
  version: number;
  opened_at: string;
  updated_at: string;
  timeline_entries: number;
}

export interface IncidentTimelineEntry {
  id: number;
  entry_type: string;
  actor_type: 'system' | 'human' | 'agent' | 'integration';
  actor_id: string | null;
  actor_name: string | null;
  from_status: IncidentStatus | null;
  to_status: IncidentStatus | null;
  summary: string;
  evidence_type: string | null;
  evidence_ref: string | null;
  occurred_at: string;
}

export interface IncidentDetail extends IncidentSummary {
  hypothesis: string | null;
  confidence: number | null;
  resolution_code: string | null;
  resolution_notes: string | null;
  false_positive: boolean;
  timeline: IncidentTimelineEntry[];
  timeline_total: number;
  timeline_truncated: boolean;
}

export interface IncidentListResponse {
  schema_version: 'incident-list.v1';
  total: number;
  limit: number;
  offset: number;
  incidents: IncidentSummary[];
}

export interface IncidentDetailResponse {
  schema_version: 'incident-detail.v1';
  incident: IncidentDetail;
}
