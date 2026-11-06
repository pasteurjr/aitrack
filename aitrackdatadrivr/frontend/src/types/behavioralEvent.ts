export interface BehavioralEvent {
  device_id: string;
  type: string;
  timestamp: string;
  severity: string;
  icon: string;
  lat: number;
  lon: number;
  episode_id?: string;
  episode_state?: string;
}
