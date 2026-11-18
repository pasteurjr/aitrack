export type SensorSupportStatus = 'confirmed' | 'unavailable' | 'unknown';
export type SensorLifecycleStatus = 'active' | 'inactive';
export type SensorHealthStatus = 'current' | 'stale' | 'invalid' | 'unavailable';

export interface SensorReadingDTO {
  value: boolean | number | string | Record<string, unknown>;
  value_type: 'boolean' | 'number' | 'string' | 'geo' | 'json';
  unit: string | null;
  quality: 'valid' | 'invalid' | 'estimated' | 'unknown';
  observed_at: string;
  received_at: string;
  recorded_at: string;
  age_seconds: number;
  clock_skew_seconds: number | null;
  observed_timezone: 'unspecified';
  received_timezone: string;
}

export interface VehicleSensorDTO {
  id: number;
  source_code: 'tracker' | 'dirijabem';
  protocol_code: string;
  device_model: string;
  external_device_id: string;
  capability_code: string;
  unit: string | null;
  lifecycle_status: SensorLifecycleStatus;
  first_seen_at: string;
  last_seen_at: string;
  support_status: SensorSupportStatus;
  evidence: string | null;
  configured: true;
  health_status: SensorHealthStatus;
  latest_reading: SensorReadingDTO | null;
}

export interface VehicleSensorsResponse {
  schema_version: 'vehicle-sensors.v1';
  vehicle: {
    id: number;
    public_id: string;
    plate: string | null;
    active: boolean;
  };
  sources: string[];
  protocols: string[];
  commands: Array<{
    protocol_code: string;
    capability_code: string;
    support_status: SensorSupportStatus;
    evidence: string;
  }>;
  confirmed_commands: VehicleSensorsResponse['commands'];
  count: number;
  sensors: VehicleSensorDTO[];
}

export interface DetectorPolicyDTO {
  id: number;
  policy_key: string;
  version_number: number;
  detector_type: string;
  capability_code: string | null;
  scope_type: 'global' | 'source' | 'monitor' | 'vehicle';
  scope_ref: string;
  parameters: Record<string, unknown>;
  status: 'draft' | 'active' | 'superseded' | 'retired';
}

export interface DetectorPoliciesResponse {
  schema_version: 'detector-policies.v1';
  count: number;
  policies: DetectorPolicyDTO[];
}

export interface VehicleSecurityStateDTO {
  schema_version: 'vehicle-security-state.v1';
  vehicle_id: number;
  state: 'disarmed' | 'armed';
  version: number;
  changed_by: { type: 'human' | 'system'; id: string; name: string };
  authorization_basis: 'owner_request' | 'operator_protocol' | 'scheduled_policy' | 'migration';
  reason: string;
  changed_at: string;
  history: Array<{
    id: number;
    from_state: 'disarmed' | 'armed';
    to_state: 'disarmed' | 'armed';
    actor_name: string;
    authorization_basis: string;
    reason: string;
    correlation_id: string;
    occurred_at: string;
  }>;
  idempotent: boolean;
}
