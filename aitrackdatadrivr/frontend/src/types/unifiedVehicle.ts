export const UNIFIED_VEHICLE_SCHEMA_VERSION = 'vehicle.v1' as const;

export type VehicleIdentityType = 'tracker_only' | 'app_only' | 'both';

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
  tracker: TrackerIdentityDTO | null;
  dirijabem: DirijabemIdentityDTO | null;
}

export function isUnifiedVehicleDTO(value: unknown): value is UnifiedVehicleDTO {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<UnifiedVehicleDTO>;
  if (
    candidate.schema_version !== UNIFIED_VEHICLE_SCHEMA_VERSION
    || typeof candidate.vehicle_id !== 'number'
    || typeof candidate.display_name !== 'string'
    || typeof candidate.active !== 'boolean'
  ) return false;

  if (candidate.identity_type === 'tracker_only') {
    return Boolean(candidate.tracker) && candidate.dirijabem === null;
  }
  if (candidate.identity_type === 'app_only') {
    return candidate.tracker === null && Boolean(candidate.dirijabem);
  }
  if (candidate.identity_type === 'both') {
    return Boolean(candidate.tracker) && Boolean(candidate.dirijabem);
  }
  return false;
}
