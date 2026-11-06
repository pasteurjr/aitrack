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

export function behavioralEventId(event: BehavioralEvent): string {
  return event.episode_id
    ?? `${event.device_id}:${event.type}:${event.timestamp}:${event.lat}:${event.lon}`;
}
