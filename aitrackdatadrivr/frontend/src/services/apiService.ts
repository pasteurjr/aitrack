/**
 * API Service Layer
 * Provides typed API calls to the Flask backend
 * Centraliza consultas reais ao backend e aos bancos integrados.
 */

import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import type { UnifiedVehiclesResponse } from '../types/unifiedVehicle';
import type { RuntimeEnvironment } from '../types/runtimeEnvironment';
import type { DetectorEpisodesResponse, DetectorPoliciesResponse, DetectorPolicyDTO, VehicleSecurityStateDTO, VehicleSensorsResponse } from '../types/sensor';
import type { EventStats, EventType, MonitorEvent } from '../types/monitorEvent';
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
  ArchiveGeofenceBody,
  GeofenceDetailResponse,
  GeofenceAssignment,
  GeofenceAssignmentOptions,
  AssignmentTargetType,
  GeofenceListResponse,
  GeofenceLiveStateResponse,
  UpdateGeofenceAssignmentBody,
  UpdateGeofenceBody,
} from '../types/geofence';
import type { AgentConfigurationsResponse, AgentDefinitionsResponse, AutonomyLevel, AutonomousRisk } from '../types/agent';
import type { AgentRunsResponse, AgentRunStatus } from '../types/agentRun';
import type { TripReplayResponse } from '../types/tripReplay';
import type { AnalyticsSource, BehaviorAnalyticsResponse } from '../types/analytics';
import type { BehaviorReport, ReportExport, ReportExportSchedule, ReportMode } from '../types/report';
import type { OperationsMetrics } from '../types/operationsMetrics';
import type { AuthSession } from '../types/auth';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
});

apiClient.interceptors.request.use(config => {
  if (typeof document !== 'undefined' && ['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
    const csrf = document.cookie.split('; ').find(item => item.startsWith('aitrack_csrf='))?.split('=', 2)[1];
    if (csrf) config.headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  return config;
});

export const authService = {
  me: () => apiClient.get<AuthSession>('/auth/me'),
  login: (email: string, password: string) => apiClient.post<AuthSession>('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
  recover: (email: string) => apiClient.post('/auth/recover', { email }),
};

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
    incident_type?: string;
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
  getCatalog: () => apiClient.get<EventType[]>('/events/catalog'),

  /**
   * Get all events with optional filters
   */
  getAll: (filters?: { limit?: number; device_id?: string; categoria?: string }) =>
    apiClient.get<MonitorEvent[]>('/events', { params: filters }),

  /**
   * Get event statistics
   */
  getStats: () => apiClient.get<EventStats>('/events/stats'),
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

export const sensorService = {
  getByVehicle: (vehicleId: number) =>
    apiClient.get<VehicleSensorsResponse>(`/vehicles/${vehicleId}/sensors`),
  getEpisodes: (vehicleId: number, status?: 'open' | 'resolved') =>
    apiClient.get<DetectorEpisodesResponse>(`/vehicles/${vehicleId}/detector-episodes`, {
      params: { status },
    }),
};

export const detectorPolicyService = {
  getAll: () => apiClient.get<DetectorPoliciesResponse>('/detector-policies'),
  activate: (policyId: number, body: { actor: string; reason: string; correlation_id: string }) =>
    apiClient.post<DetectorPolicyDTO>(`/detector-policies/${policyId}/activate`, body),
};

export const agentConfigurationService = {
  getAgents: () => apiClient.get<AgentDefinitionsResponse>('/agent-configurations/agents'),
  getConfigurations: () => apiClient.get<AgentConfigurationsResponse>('/agent-configurations'),
  getTools: () => apiClient.get<{ schema_version: string; tools: string[] }>('/agent-configurations/tools'),
  create: (body: Record<string, unknown>) => apiClient.post('/agent-configurations', body),
  addTool: (configId: number, body: Record<string, unknown>) =>
    apiClient.post(`/agent-configurations/${configId}/tools`, body),
  addAutonomy: (configId: number, body: { policy: { autonomy_level: AutonomyLevel; execution_mode: 'simulation'|'live'; max_autonomous_risk: AutonomousRisk; allowed_autonomous_actions: string[] }; actor: string; reason: string }) =>
    apiClient.post(`/agent-configurations/${configId}/autonomy`, body),
  activate: (configId: number, body: { actor: string; reason: string }) =>
    apiClient.post(`/agent-configurations/${configId}/activate`, body),
};

export const agentRunService = {
  getAll: (filters?: { agent_key?: string; status?: AgentRunStatus | ''; correlation_id?: string; limit?: number }) =>
    apiClient.get<AgentRunsResponse>('/agent-runs', { params: filters }),
};

export interface InternalNotification { id:number;public_id:string;incident_id:number;recipient_ref:string;title:string;body:string;priority:'low'|'normal'|'high'|'urgent';version:number;unread:boolean;created_at:string;read_at:string|null;action_public_id:string;action_version:number }
export const internalNotificationService = {
  getAll: (recipient_ref='operations',unread_only=false) => apiClient.get<{schema_version:string;count:number;notifications:InternalNotification[]}>('/internal-notifications',{params:{recipient_ref,unread_only}}),
  markRead: (publicId:string,body:{expected_version:number;actor_id:string;idempotency_key:string}) => apiClient.post(`/internal-notifications/${publicId}/read`,body),
};

export const securityStateService = {
  getByVehicle: (vehicleId: number) =>
    apiClient.get<VehicleSecurityStateDTO>(`/vehicles/${vehicleId}/security-state`),
  transition: (vehicleId: number, body: {
    target_state: 'armed' | 'disarmed';
    expected_version: number;
    actor: { type: 'human'; id: string; name: string };
    authorization_basis: 'owner_request' | 'operator_protocol';
    reason: string;
    correlation_id: string;
  }) => apiClient.post<VehicleSecurityStateDTO>(
    `/vehicles/${vehicleId}/security-state/transitions`, body,
  ),
};

export const runtimeEnvironmentService = {
  getCurrent: () => apiClient.get<RuntimeEnvironment>('/runtime/environment'),
};

export const tripReplayService = {
  getByExecution: (executionId: string, positionLimit = 5000) =>
    apiClient.get<TripReplayResponse>(`/routes/executions/${executionId}/replay`, {
      params: { position_limit: positionLimit },
    }),
};

export const analyticsService = {
  getBehavior: (filters: {
    from: string;
    to: string;
    timezone: string;
    sources: AnalyticsSource[];
    comparison: 'none' | 'previous';
  }) => apiClient.get<BehaviorAnalyticsResponse>('/analytics/behavior', {
    params: { ...filters, sources: filters.sources.join(',') },
  }),
  getOperations: (filters: { from: string; to: string; timezone: string }) =>
    apiClient.get<OperationsMetrics>('/analytics/operations', { params: filters }),
};

export const reportService = {
  generateBehavior: (body: { mode: ReportMode; from: string; to: string; timezone: string; actor_id: string }) =>
    apiClient.post<BehaviorReport>('/reports/behavior', body),
  exportBehavior: (body: { mode: ReportMode; from: string; to: string; timezone: string; actor_id: string; format: 'csv'|'json'; idempotency_key: string }) =>
    apiClient.post<ReportExport>('/report-exports', body),
  createSchedule: (body: { mode: ReportMode; format: 'csv'|'json'; timezone: string; cadence: 'daily'|'weekly'; local_time: string; weekday?: number; actor_id: string; filters: Record<string, unknown> }) =>
    apiClient.post<ReportExportSchedule>('/report-exports/schedules', body),
};

// ==================== Geofence Services ====================

export const geofenceService = {
  getAll: (params?: { status?: string; regra?: string; search?: string; limit?: number }) =>
    apiClient.get<GeofenceListResponse>('/geofences', { params }),

  getLiveState: (limit = 200) =>
    apiClient.get<GeofenceLiveStateResponse>('/geofences/live-state', { params: { limit } }),

  create: (body: CreateGeofenceBody) =>
    apiClient.post<GeofenceDetailResponse>('/geofences', body),

  update: (reference: string, body: UpdateGeofenceBody) =>
    apiClient.put<GeofenceDetailResponse>(`/geofences/${reference}`, body),

  archive: (reference: string, body: ArchiveGeofenceBody) =>
    apiClient.delete<GeofenceDetailResponse>(`/geofences/${reference}`, { data: body }),

  getAssignmentOptions: () =>
    apiClient.get<GeofenceAssignmentOptions>('/geofences/assignment-options'),

  getAssignments: (reference: string) =>
    apiClient.get<{ schema_version: string; assignments: GeofenceAssignment[] }>(
      `/geofences/${reference}/assignments`,
    ),

  assign: (reference: string, body: {
    target_type: AssignmentTargetType;
    target_id: number;
    operator: { id: string; name: string };
  }) => apiClient.post<{ schema_version: string; assignment: GeofenceAssignment }>(
    `/geofences/${reference}/assignments`, body,
  ),

  updateAssignment: (
    reference: string,
    assignmentId: number,
    body: UpdateGeofenceAssignmentBody,
  ) => apiClient.put<{ schema_version: string; assignment: GeofenceAssignment }>(
    `/geofences/${reference}/assignments/${assignmentId}`, body,
  ),

  deactivateAssignment: (reference: string, assignmentId: number, body: {
    expected_version: number;
    operator: { id: string; name: string };
  }) => apiClient.delete<{ schema_version: string; assignment: GeofenceAssignment }>(
    `/geofences/${reference}/assignments/${assignmentId}`, { data: body },
  ),

  createGroup: (body: {
    nome: string;
    vehicle_ids: number[];
    driver_ids: number[];
    operator: { id: string; name: string };
  }) => apiClient.post<{ schema_version: string; group: import('../types/geofence').AssignmentOption }>(
    '/geofences/monitoring-groups', body,
  ),
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
  sensor: sensorService,
  detectorPolicy: detectorPolicyService,
  securityState: securityStateService,
  runtimeEnvironment: runtimeEnvironmentService,
};

export default apiService;
