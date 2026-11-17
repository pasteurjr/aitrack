export type SensorSupportStatus = 'confirmed' | 'unavailable' | 'unknown';
export type SensorLifecycleStatus = 'active' | 'inactive';

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
