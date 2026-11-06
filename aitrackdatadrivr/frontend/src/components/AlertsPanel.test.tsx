import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { incidentService, unifiedVehicleService } from '../services/apiService';
import AlertsPanel from './AlertsPanel';

jest.mock('../services/apiService', () => ({
  incidentService: {
    getAll: jest.fn(),
    getById: jest.fn(),
    acknowledge: jest.fn(),
    assume: jest.fn(),
    comment: jest.fn(),
    getClassificationCatalog: jest.fn(),
    resolve: jest.fn(),
    classifyFalsePositive: jest.fn(),
    reportFalseNegative: jest.fn(),
  },
  unifiedVehicleService: { getAll: jest.fn() },
}));

const mockedIncidentService = incidentService as jest.Mocked<typeof incidentService>;
const mockedUnifiedVehicleService = unifiedVehicleService as jest.Mocked<typeof unifiedVehicleService>;

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
  sla_due_at: '2026-11-06T15:05:00',
  sla_status: 'at_risk',
  sla_seconds_remaining: 120,
  sla_progress_percent: 60,
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
  window.localStorage.clear();
  mockedIncidentService.getAll.mockResolvedValue(listResponse([]) as never);
  mockedIncidentService.acknowledge.mockResolvedValue({ data: {} } as never);
  mockedIncidentService.assume.mockResolvedValue({ data: {} } as never);
  mockedIncidentService.comment.mockResolvedValue({ data: {} } as never);
  mockedIncidentService.getClassificationCatalog.mockResolvedValue({
    data: {
      schema_version: 'incident-classification.v1',
      true_positive_reasons: ['confirmed_risk'],
      false_positive_reasons: ['sensor_noise'],
      false_negative_reasons: ['detector_gap'],
    },
  } as never);
  mockedIncidentService.resolve.mockResolvedValue({ data: {} } as never);
  mockedIncidentService.classifyFalsePositive.mockResolvedValue({ data: {} } as never);
  mockedIncidentService.reportFalseNegative.mockResolvedValue({ data: {} } as never);
  mockedUnifiedVehicleService.getAll.mockResolvedValue({ data: { vehicles: [] } } as never);
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
  expect(screen.getByText('SLA em risco')).toBeInTheDocument();
  expect(screen.getByText(/2min restante/)).toBeInTheDocument();

  fireEvent.click(title);

  expect(await screen.findByText('Timeline auditável (1)')).toBeInTheDocument();
  expect(screen.getByText('Evidência speeding recebida de tracker')).toBeInTheDocument();
  expect(screen.getByText('Ações do operador')).toBeInTheDocument();
  expect(mockedIncidentService.getById).toHaveBeenCalledWith(44);

  fireEvent.change(screen.getByLabelText('Seu nome'), { target: { value: 'Maria Operadora' } });
  fireEvent.click(screen.getByRole('button', { name: 'Reconhecer incidente' }));

  await waitFor(() => expect(mockedIncidentService.acknowledge).toHaveBeenCalledWith(
    44,
    expect.objectContaining({
      expected_version: 2,
      operator: expect.objectContaining({ name: 'Maria Operadora' }),
    }),
  ));
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

it('exige motivo e confirmação explícita para classificar falso positivo', async () => {
  const triageIncident = { ...incident, status: 'triage', version: 3 } as const;
  mockedIncidentService.getAll.mockResolvedValue(listResponse([triageIncident]) as never);
  mockedIncidentService.getById.mockResolvedValue({
    data: {
      schema_version: 'incident-detail.v1',
      incident: {
        ...triageIncident,
        hypothesis: null, confidence: null, resolution_code: null, resolution_notes: null,
        false_positive: false, detection_outcome: 'unreviewed', classification_reason: null,
        classified_by: null, classified_at: null, timeline_total: 0,
        timeline_truncated: false, timeline: [],
      },
    },
  } as never);
  const confirm = jest.spyOn(window, 'confirm').mockReturnValue(true);

  render(<AlertsPanel />);
  fireEvent.click(await screen.findByText('Excesso de velocidade detectado'));
  await screen.findByText('Encerrar análise da detecção');
  fireEvent.change(screen.getByLabelText('Seu nome'), { target: { value: 'Maria Operadora' } });
  fireEvent.change(screen.getByLabelText('Motivo da classificação'), { target: { value: 'sensor_noise' } });
  fireEvent.change(screen.getByLabelText('Justificativa da classificação'), {
    target: { value: 'Ruído do sensor confirmado pela telemetria redundante.' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Classificar como falso positivo' }));

  await waitFor(() => expect(mockedIncidentService.classifyFalsePositive).toHaveBeenCalledWith(
    44,
    expect.objectContaining({
      expected_version: 3,
      classification_reason: 'sensor_noise',
    }),
  ));
  expect(confirm).toHaveBeenCalled();
  confirm.mockRestore();
});

it('registra falso negativo com veículo e taxonomia explícitos', async () => {
  mockedUnifiedVehicleService.getAll.mockResolvedValue({
    data: {
      vehicles: [{ vehicle_id: 12, display_name: 'Veículo 12', active: true }],
    },
  } as never);
  render(<AlertsPanel />);
  await screen.findByText('Fila sem incidentes');

  fireEvent.click(screen.getByRole('button', { name: 'Registrar falso negativo' }));
  await waitFor(() => expect(mockedUnifiedVehicleService.getAll).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText('Operador do falso negativo'), { target: { value: 'Maria Operadora' } });
  fireEvent.change(screen.getByLabelText('Veículo do falso negativo'), { target: { value: '12' } });
  fireEvent.change(screen.getByLabelText('Tipo do falso negativo'), { target: { value: 'geofence_exit' } });
  fireEvent.change(screen.getByLabelText('Motivo do falso negativo'), { target: { value: 'detector_gap' } });
  fireEvent.change(screen.getByLabelText('Título do falso negativo'), { target: { value: 'Saída não detectada' } });
  fireEvent.change(screen.getByLabelText('Evidência do falso negativo'), {
    target: { value: 'Saída confirmada por câmera e controle da portaria.' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar falha de detecção' }));

  await waitFor(() => expect(mockedIncidentService.reportFalseNegative).toHaveBeenCalledWith(
    expect.objectContaining({
      vehicle_id: 12,
      incident_type: 'geofence_exit',
      classification_reason: 'detector_gap',
    }),
  ));
});
