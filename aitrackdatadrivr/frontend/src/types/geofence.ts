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

export interface GeofenceDetailResponse {
  schema_version: 'geofence-detail.v1';
  geofence: Geofence;
}
