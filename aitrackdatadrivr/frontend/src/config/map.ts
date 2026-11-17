const DEFAULT_MAP_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

export function resolveMapTileUrl(value?: string): string {
  return value?.trim() || DEFAULT_MAP_TILE_URL;
}

export const MAP_TILE_URL = resolveMapTileUrl(process.env.REACT_APP_MAP_TILE_URL);
export const MAP_TILE_ATTRIBUTION = '&copy; OpenStreetMap contributors';
