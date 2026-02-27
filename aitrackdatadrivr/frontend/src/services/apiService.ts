/**
 * API Service Layer
 * Provides typed API calls to the Flask backend
 * Replaces all mock data with real database queries
 */

import axios from 'axios';

const API_BASE = 'http://localhost:5009/api';

// ==================== Monitor Services ====================

export const monitorService = {
  /**
   * Get all monitors
   */
  getAll: () => axios.get(`${API_BASE}/monitors`),

  /**
   * Get monitor by ID
   */
  getById: (id: number) => axios.get(`${API_BASE}/monitors/${id}`),

  /**
   * Get vehicles in a monitor
   */
  getVehicles: (id: number) => axios.get(`${API_BASE}/monitors/${id}/vehicles`),

  /**
   * Get analyses for a monitor
   */
  getAnalyses: (id: number, limit?: number) =>
    axios.get(`${API_BASE}/monitors/${id}/analyses`, { params: { limit } }),

  /**
   * Create new monitor
   */
  create: (data: any) => axios.post(`${API_BASE}/monitors`, data),

  /**
   * Update monitor
   */
  update: (id: number, data: any) => axios.put(`${API_BASE}/monitors/${id}`, data),

  /**
   * Toggle monitor active status
   */
  toggle: (id: number, ativo: boolean) =>
    axios.post(`${API_BASE}/monitors/${id}/toggle`, { ativo }),

  /**
   * Get monitor statistics
   */
  getStats: () => axios.get(`${API_BASE}/monitors/stats`),
};

// ==================== Alert Services ====================

export const alertService = {
  /**
   * Get all alerts with optional filters
   */
  getAll: (filters?: { status?: string; severidade?: string; monitor_id?: number }) =>
    axios.get(`${API_BASE}/alerts`, { params: filters }),

  /**
   * Get alert by ID
   */
  getById: (id: number) => axios.get(`${API_BASE}/alerts/${id}`),

  /**
   * Acknowledge alert
   */
  acknowledge: (id: number, reconhecido_por: string) =>
    axios.put(`${API_BASE}/alerts/${id}/acknowledge`, { reconhecido_por }),

  /**
   * Resolve alert
   */
  resolve: (id: number) => axios.put(`${API_BASE}/alerts/${id}/resolve`),

  /**
   * Dismiss alert
   */
  dismiss: (id: number) => axios.put(`${API_BASE}/alerts/${id}/dismiss`),

  /**
   * Get alert statistics
   */
  getStats: () => axios.get(`${API_BASE}/alerts/stats`),
};

// ==================== Event Services ====================

export const eventService = {
  /**
   * Get event catalog (tipos de eventos)
   */
  getCatalog: () => axios.get(`${API_BASE}/events/catalog`),

  /**
   * Get all events with optional filters
   */
  getAll: (filters?: { limit?: number; device_id?: string; categoria?: string }) =>
    axios.get(`${API_BASE}/events`, { params: filters }),

  /**
   * Get event statistics
   */
  getStats: () => axios.get(`${API_BASE}/events/stats`),
};

// ==================== Vehicle Services ====================

export const vehicleService = {
  /**
   * Add vehicle to monitor
   */
  addToMonitor: (monitorId: number, veicod: number, device_id: string) =>
    axios.post(`${API_BASE}/monitors/${monitorId}/vehicles`, { veicod, device_id }),

  /**
   * Remove vehicle from monitor
   */
  removeFromMonitor: (veiculomonitorId: number) =>
    axios.delete(`${API_BASE}/monitors/vehicles/${veiculomonitorId}`),
};

// ==================== Fleet Services (Behavioral Engine) ====================

export const fleetService = {
  /**
   * Get all vehicle scores
   */
  getScores: () => axios.get(`${API_BASE}/fleet/scores`),

  /**
   * Get recent behavioral events
   */
  getEvents: (limit?: number, device_id?: string) =>
    axios.get(`${API_BASE}/fleet/events`, { params: { limit, device_id } }),

  /**
   * Get fleet statistics
   */
  getStats: () => axios.get(`${API_BASE}/fleet/stats`),

  /**
   * Get score for specific vehicle
   */
  getVehicleScore: (device_id: string) =>
    axios.get(`${API_BASE}/vehicles/${device_id}/score`),
};

export default {
  monitor: monitorService,
  alert: alertService,
  event: eventService,
  vehicle: vehicleService,
  fleet: fleetService,
};
