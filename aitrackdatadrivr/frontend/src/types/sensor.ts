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
  count: number;
  sensors: VehicleSensorDTO[];
}
