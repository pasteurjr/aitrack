import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { incidentService } from '../services/apiService';
import AlertsPanel from './AlertsPanel';

jest.mock('../services/apiService', () => ({
  incidentService: {
    getAll: jest.fn(),
    getById: jest.fn(),
  },
}));

const mockedIncidentService = incidentService as jest.Mocked<typeof incidentService>;

const incident = {
  id: 44,
  vehicle_id: 12,
  device_id: 'SIM-1001',
  codusu: null,
  placa: 'ABC1D23',
  vehicle_name: 'Veículo 1',
  monitor_id: null,
  monitor_name: null,
  incident_type: 'speeding',
  title: 'Excesso de velocidade detectado',
  summary: 'Episódio speeding recebido de tracker.',
  status: 'new',
  severity: 'critical',
  risk_score: 30,
  primary_source: 'tracker',
  assigned_type: null,
  assigned_to: null,
  latitude: -23.55,
  longitude: -46.63,
  event_count: 1,
  version: 2,
  opened_at: '2026-11-06T15:00:00',
  updated_at: '2026-11-06T15:00:00',
  timeline_entries: 1,
} as const;

const listResponse = (incidents: unknown[]) => ({
  data: {
    schema_version: 'incident-list.v1',
    total: incidents.length,
    limit: 200,
    offset: 0,
    incidents,
  },
});

beforeEach(() => {
  jest.clearAllMocks();
  mockedIncidentService.getAll.mockResolvedValue(listResponse([]) as never);
});

it('consulta somente incidentes abertos e exibe estado vazio real', async () => {
  render(<AlertsPanel />);

  expect(screen.getByText('Consultando a fila operacional de incidentes.')).toBeInTheDocument();
  expect(await screen.findByText('Fila sem incidentes')).toBeInTheDocument();
  expect(mockedIncidentService.getAll).toHaveBeenCalledWith({ limit: 200, open_only: true });
  expect(screen.queryByRole('note', { name: 'Conteúdo de demonstração' })).not.toBeInTheDocument();
});

it('renderiza incidente real e abre seu detalhe auditável', async () => {
  mockedIncidentService.getAll.mockResolvedValue(listResponse([incident]) as never);
  mockedIncidentService.getById.mockResolvedValue({
    data: {
      schema_version: 'incident-detail.v1',
      incident: {
        ...incident,
        hypothesis: null,
        confidence: null,
        resolution_code: null,
        resolution_notes: null,
        false_positive: false,
        timeline_total: 1,
        timeline_truncated: false,
        timeline: [{
          id: 90,
          entry_type: 'evidence_added',
          actor_type: 'integration',
          actor_id: 'tracker',
          actor_name: 'Integração tracker',
          from_status: null,
          to_status: null,
          summary: 'Evidência speeding recebida de tracker',
          evidence_type: 'behavior_episode',
          evidence_ref: '900',
          occurred_at: '2026-11-06T15:00:00',
        }],
      },
    },
  } as never);

  render(<AlertsPanel />);
  const title = await screen.findByText('Excesso de velocidade detectado');
  expect(screen.getAllByText('Crítica')).toHaveLength(2);
  expect(screen.getByText(/#44 · Tracker/)).toBeInTheDocument();

  fireEvent.click(title);

  expect(await screen.findByText('Timeline auditável (1)')).toBeInTheDocument();
  expect(screen.getByText('Evidência speeding recebida de tracker')).toBeInTheDocument();
  expect(screen.getByText('Ações ainda bloqueadas nesta tela')).toBeInTheDocument();
  expect(mockedIncidentService.getById).toHaveBeenCalledWith(44);
});

it('envia filtros reais de estado e severidade ao backend', async () => {
  render(<AlertsPanel />);
  await screen.findByText('Fila sem incidentes');

  fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'escalated' } });
  fireEvent.change(screen.getByLabelText('Severidade'), { target: { value: 'critical' } });

  await waitFor(() => expect(mockedIncidentService.getAll).toHaveBeenLastCalledWith({
    limit: 200,
    status: 'escalated',
    severity: 'critical',
  }));
});

it('não inventa dados quando a API falha e permite tentar novamente', async () => {
  mockedIncidentService.getAll
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(listResponse([]) as never);

  render(<AlertsPanel />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Nenhum alerta foi inventado');
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

  expect(await screen.findByText('Fila sem incidentes')).toBeInTheDocument();
  expect(mockedIncidentService.getAll).toHaveBeenCalledTimes(2);
});
