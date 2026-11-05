const DEFAULT_API_BASE_URL = 'http://localhost:5009/api';

export function resolveApiBaseUrl(value?: string): string {
  const configuredValue = value?.trim();
  return (configuredValue || DEFAULT_API_BASE_URL).replace(/\/+$/, '');
}

export const API_BASE_URL = resolveApiBaseUrl(process.env.REACT_APP_API_BASE_URL);
