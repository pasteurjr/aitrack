export type ReplayEventKind = 'execution' | 'position' | 'episode_started' | 'episode_recovered';

export interface ReplayEvent {
  kind: ReplayEventKind;
  stable_id: string;
  occurred_at: string;
  longitude?: number;
  latitude?: number;
  speed_kmh?: number | null;
  distance_meters?: number | null;
  episode_type?: 'deviation' | 'unplanned_stop';
  event_type?: string;
  to_status?: string;
}

export interface TripReplayResponse {
  schema_version: 'trip-replay.v1';
  mode: 'replay';
  read_only: true;
  execution: {
    public_id: string;
    status: string;
    planned_start_at: string;
    planned_end_at: string;
    route_version: number;
  };
  planned_route: {
    geometry: { type: 'LineString'; coordinates: [number, number][] };
    corridor_meters: number;
  };
  positions: ReplayEvent[];
  timeline: ReplayEvent[];
  truncated: boolean;
  position_limit: number;
}
