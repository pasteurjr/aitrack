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
  ativo: boolean;
  version: number;
}
