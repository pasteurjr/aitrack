export const UNIFIED_VEHICLE_SCHEMA_VERSION = 'vehicle.v1' as const;

export type VehicleIdentityType = 'tracker_only' | 'app_only' | 'both';
export type TelemetrySource = 'tracker' | 'dirijabem';
export type OperationMode = 'live' | 'simulation' | 'replay' | 'synthetic' | 'unknown';

export interface TelemetryProvenanceDTO {
  source: TelemetrySource;
  mode: OperationMode;
  last_communication_at: string | null;
}

export interface TrackerIdentityDTO {
  device_id: string;
  veicod: number | null;
}

export interface DirijabemIdentityDTO {
  codusu: number;
}

export interface UnifiedVehicleDTO {
  schema_version: typeof UNIFIED_VEHICLE_SCHEMA_VERSION;
  vehicle_id: number;
  identity_type: VehicleIdentityType;
  display_name: string;
  plate: string | null;
  active: boolean;
  telemetry: TelemetryProvenanceDTO[];
  tracker: TrackerIdentityDTO | null;
  dirijabem: DirijabemIdentityDTO | null;
}

export interface UnifiedVehiclesResponse {
  schema_version: typeof UNIFIED_VEHICLE_SCHEMA_VERSION;
  total: number;
  vehicles: UnifiedVehicleDTO[];
}

export function isUnifiedVehicleDTO(value: unknown): value is UnifiedVehicleDTO {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<UnifiedVehicleDTO>;
  if (
    candidate.schema_version !== UNIFIED_VEHICLE_SCHEMA_VERSION
    || typeof candidate.vehicle_id !== 'number'
    || typeof candidate.display_name !== 'string'
    || typeof candidate.active !== 'boolean'
    || !Array.isArray(candidate.telemetry)
  ) return false;

  const telemetrySources = candidate.telemetry.map(item => item?.source);
  const hasTelemetry = (source: TelemetrySource) => telemetrySources.includes(source);

  if (candidate.identity_type === 'tracker_only') {
    return Boolean(candidate.tracker) && candidate.dirijabem === null
      && candidate.telemetry.length === 1 && hasTelemetry('tracker');
  }
  if (candidate.identity_type === 'app_only') {
    return candidate.tracker === null && Boolean(candidate.dirijabem)
      && candidate.telemetry.length === 1 && hasTelemetry('dirijabem');
  }
  if (candidate.identity_type === 'both') {
    return Boolean(candidate.tracker) && Boolean(candidate.dirijabem)
      && candidate.telemetry.length === 2
      && hasTelemetry('tracker') && hasTelemetry('dirijabem');
  }
  return false;
}
