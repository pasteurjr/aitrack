/**
 * API Service Layer
 * Provides typed API calls to the Flask backend
 * Replaces all mock data with real database queries
 */

import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import type { UnifiedVehiclesResponse } from '../types/unifiedVehicle';
import type {
  IncidentDetailResponse,
  IncidentCommandBody,
  IncidentClassificationCatalog,
  IncidentListResponse,
  IncidentSeverity,
  IncidentStatus,
} from '../types/incident';
import type {
  CreateGeofenceBody,
  GeofenceDetailResponse,
  GeofenceListResponse,
} from '../types/geofence';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// ==================== Monitor Services ====================

export const monitorService = {
  /**
   * Get all monitors
   */
  getAll: () => apiClient.get('/monitors'),

  /**
   * Get monitor by ID
   */
  getById: (id: number) => apiClient.get(`/monitors/${id}`),

  /**
   * Get vehicles in a monitor
   */
  getVehicles: (id: number) => apiClient.get(`/monitors/${id}/vehicles`),

  /**
   * Get analyses for a monitor
   */
  getAnalyses: (id: number, limit?: number) =>
    apiClient.get(`/monitors/${id}/analyses`, { params: { limit } }),

  /**
   * Create new monitor
   */
  create: (data: any) => apiClient.post('/monitors', data),

  /**
   * Update monitor
   */
  update: (id: number, data: any) => apiClient.put(`/monitors/${id}`, data),

  /**
   * Toggle monitor active status
   */
  toggle: (id: number, ativo: boolean) =>
    apiClient.post(`/monitors/${id}/toggle`, { ativo }),

  /**
   * Get monitor statistics
   */
  getStats: () => apiClient.get('/monitors/stats'),
};

// ==================== Alert Services ====================

export const alertService = {
  /**
   * Get all alerts with optional filters
   */
  getAll: (filters?: { status?: string; severidade?: string; monitor_id?: number }) =>
    apiClient.get('/alerts', { params: filters }),

  /**
   * Get alert by ID
   */
  getById: (id: number) => apiClient.get(`/alerts/${id}`),

  /**
   * Acknowledge alert
   */
  acknowledge: (id: number, reconhecido_por: string) =>
    apiClient.put(`/alerts/${id}/acknowledge`, { reconhecido_por }),

  /**
   * Resolve alert
   */
  resolve: (id: number) => apiClient.put(`/alerts/${id}/resolve`),

  /**
   * Dismiss alert
   */
  dismiss: (id: number) => apiClient.put(`/alerts/${id}/dismiss`),

  /**
   * Get alert statistics
   */
  getStats: () => apiClient.get('/alerts/stats'),
};

// ==================== Incident Services ====================

export const incidentService = {
  getAll: (filters?: {
    status?: IncidentStatus;
    severity?: IncidentSeverity;
    open_only?: boolean;
    limit?: number;
    offset?: number;
  }) => apiClient.get<IncidentListResponse>('/incidents', { params: filters }),

  getById: (id: number, timelineLimit = 200) =>
    apiClient.get<IncidentDetailResponse>(`/incidents/${id}`, {
      params: { timeline_limit: timelineLimit },
    }),

  acknowledge: (id: number, body: IncidentCommandBody) =>
    apiClient.post(`/incidents/${id}/acknowledge`, body),

  assume: (id: number, body: IncidentCommandBody) =>
    apiClient.post(`/incidents/${id}/assume`, body),

  comment: (id: number, body: IncidentCommandBody & { comment: string }) =>
    apiClient.post(`/incidents/${id}/comments`, body),

  getClassificationCatalog: () =>
    apiClient.get<IncidentClassificationCatalog>('/incidents/classification-catalog'),

  resolve: (id: number, body: IncidentCommandBody & {
    resolution_code: string;
    resolution_notes: string;
    classification_reason: string;
  }) => apiClient.post(`/incidents/${id}/resolve`, body),

  classifyFalsePositive: (id: number, body: IncidentCommandBody & {
    resolution_notes: string;
    classification_reason: string;
  }) => apiClient.post(`/incidents/${id}/false-positive`, body),

  reportFalseNegative: (body: Omit<IncidentCommandBody, 'expected_version'> & {
    vehicle_id: number;
    incident_type: string;
    title: string;
    notes: string;
    severity: IncidentSeverity;
    classification_reason: string;
    occurred_at: string;
  }) => apiClient.post('/incidents/false-negatives', body),
};

// ==================== Event Services ====================

export const eventService = {
  /**
   * Get event catalog (tipos de eventos)
   */
  getCatalog: () => apiClient.get('/events/catalog'),

  /**
   * Get all events with optional filters
   */
  getAll: (filters?: { limit?: number; device_id?: string; categoria?: string }) =>
    apiClient.get('/events', { params: filters }),

  /**
   * Get event statistics
   */
  getStats: () => apiClient.get('/events/stats'),
};

// ==================== Vehicle Services ====================

export const vehicleService = {
  /**
   * Add vehicle to monitor
   */
  addToMonitor: (monitorId: number, veicod: number, device_id: string) =>
    apiClient.post(`/monitors/${monitorId}/vehicles`, { veicod, device_id }),

  /**
   * Remove vehicle from monitor
   */
  removeFromMonitor: (veiculomonitorId: number) =>
    apiClient.delete(`/monitors/vehicles/${veiculomonitorId}`),
};

// ==================== Fleet Services (Behavioral Engine) ====================

export const fleetService = {
  /**
   * Get all vehicle scores
   */
  getScores: <T = Record<string, number>>() => apiClient.get<T>('/fleet/scores'),

  /**
   * Get recent behavioral events
   */
  getEvents: <T = unknown[]>(limit?: number, device_id?: string) =>
    apiClient.get<T>('/fleet/events', { params: { limit, device_id } }),

  /**
   * Get fleet statistics
   */
  getStats: <T = unknown>() => apiClient.get<T>('/fleet/stats'),

  /**
   * Get score for specific vehicle
   */
  getVehicleScore: (device_id: string) =>
    apiClient.get(`/vehicles/${device_id}/score`),
};

export const trackerService = {
  getPositions: <T = unknown[]>() => apiClient.get<T>('/posicoes'),
};

export const positionService = {
  getLatest: <T = unknown>(vehicleId: number) =>
    apiClient.get<T>(`/positions/latest/${vehicleId}`),
};

export const dirijabemService = {
  getUsers: <T = unknown[]>() => apiClient.get<T>('/dirijabem/users'),
  startUserTrip: <T = unknown>(userId: number) =>
    apiClient.post<T>(`/dirijabem/user/${userId}/start`),
  getUserRoute: <T = unknown[]>(userId: number) =>
    apiClient.get<T>(`/dirijabem/user/${userId}/route`),
  getUserLastPoint: <T = unknown>(userId: number) =>
    apiClient.get<T>(`/dirijabem/user/${userId}/last-point`),
};

export const unifiedVehicleService = {
  getAll: () => apiClient.get<UnifiedVehiclesResponse>('/v1/vehicles'),
};

// ==================== Geofence Services ====================

export const geofenceService = {
  getAll: (params?: { status?: string; regra?: string; search?: string; limit?: number }) =>
    apiClient.get<GeofenceListResponse>('/geofences', { params }),

  create: (body: CreateGeofenceBody) =>
    apiClient.post<GeofenceDetailResponse>('/geofences', body),
};

const apiService = {
  monitor: monitorService,
  alert: alertService,
  incident: incidentService,
  event: eventService,
  vehicle: vehicleService,
  fleet: fleetService,
  tracker: trackerService,
  position: positionService,
  dirijabem: dirijabemService,
  unifiedVehicle: unifiedVehicleService,
};

export default apiService;
