export type GeofenceRule = 'allowed' | 'forbidden';
export type GeofenceStatus = 'draft' | 'active' | 'inactive' | 'archived';

export interface CircleGeometry {
  type: 'Circle';
  center: [number, number];
  radius_meters: number;
}

export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: [number, number][][];
}

export type GeofenceGeometry = CircleGeometry | PolygonGeometry;

export interface Geofence {
  id: number;
  public_id: string;
  nome: string;
  descricao: string | null;
  regra: GeofenceRule;
  status: GeofenceStatus;
  version: number;
  geometry_type: 'circle' | 'polygon';
  geometry: GeofenceGeometry;
  geometry_version: number;
  active_assignments: number;
}

export interface GeofenceListResponse {
  schema_version: 'geofence-list.v1';
  total: number;
  limit: number;
  offset: number;
  geofences: Geofence[];
}

export type GeofenceStableState = 'unknown' | 'inside' | 'outside';

export interface GeofenceLiveTarget {
  assignment_id: number;
  target_type: AssignmentTargetType;
  target_label: string | null;
  subject_type: 'vehicle' | 'driver' | null;
  subject_id: number | null;
  subject_label: string | null;
  stable_state: GeofenceStableState;
  pending_state: 'inside' | 'outside' | null;
  pending_samples: number;
  policy_active: boolean;
  schedule_active: boolean;
  timezone_name: string;
  effective_from: string | null;
  effective_to: string | null;
  schedules: GeofenceAssignmentSchedule[];
  dwell_threshold_seconds: number | null;
  hysteresis_meters: number;
  is_violation: boolean;
  active_episode: boolean;
  violation_episode_id: string | null;
  violation_started_at: string | null;
  dwell_notified_at: string | null;
  last_evaluated_at: string | null;
  last_transition_at: string | null;
  last_source: 'tracker' | 'dirijabem' | null;
  last_position: {
    latitude: number;
    longitude: number;
    accuracy_m: number | null;
    signed_distance_m: number | null;
  } | null;
}

export interface LiveGeofence extends Geofence {
  targets: GeofenceLiveTarget[];
  live_summary: {
    targets: number;
    inside: number;
    outside: number;
    unknown: number;
    violations: number;
    active_episodes: number;
  };
}

export interface GeofenceLiveStateResponse {
  schema_version: 'geofence-live-state.v1';
  generated_at: string;
  refresh_after_seconds: number;
  geofences: LiveGeofence[];
}

export interface CreateGeofenceBody {
  nome: string;
  descricao?: string;
  regra: GeofenceRule;
  status: Exclude<GeofenceStatus, 'archived'>;
  geometry: GeofenceGeometry;
  operator: { id: string; name: string };
  change_reason: string;
}

export interface UpdateGeofenceBody extends CreateGeofenceBody {
  expected_version: number;
}

export interface ArchiveGeofenceBody {
  expected_version: number;
  operator: { id: string; name: string };
  change_reason: string;
}

export interface GeofenceDetailResponse {
  schema_version: 'geofence-detail.v1';
  geofence: Geofence;
}

export type AssignmentTargetType = 'vehicle' | 'driver' | 'group';

export interface AssignmentOption {
  id: number;
  public_id: string;
  label: string;
  plate?: string | null;
  codusu?: string | null;
  member_count?: number;
}

export interface GeofenceAssignmentOptions {
  schema_version: 'geofence-assignment-options.v1';
  vehicles: AssignmentOption[];
  drivers: AssignmentOption[];
  groups: AssignmentOption[];
}

export interface GeofenceAssignment {
  id: number;
  geofence_id: number;
  target_type: AssignmentTargetType;
  target_label: string;
  vehicle_id: number | null;
  driver_id: number | null;
  group_id: number | null;
  notify_on_entry: boolean;
  notify_on_exit: boolean;
  timezone_name: string;
  effective_from: string | null;
  effective_to: string | null;
  dwell_threshold_seconds: number | null;
  hysteresis_meters: number;
  schedules: GeofenceAssignmentSchedule[];
  ativo: boolean;
  version: number;
}

export interface GeofenceAssignmentSchedule {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  crosses_midnight: boolean;
  ativo: boolean;
}

export interface UpdateGeofenceAssignmentBody {
  expected_version: number;
  timezone_name: string;
  dwell_threshold_seconds: number | null;
  schedules: Array<{
    day_of_week: number;
    start_time: string;
    end_time: string;
    crosses_midnight: boolean;
  }>;
  operator: { id: string; name: string };
}
