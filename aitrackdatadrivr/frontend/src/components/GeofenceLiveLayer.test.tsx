import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import GeofenceLiveLayer from './GeofenceLiveLayer';
import { geofenceService } from '../services/apiService';


jest.mock('leaflet', () => ({
  __esModule: true,
  default: {
    DomEvent: {
      disableClickPropagation: jest.fn(),
      disableScrollPropagation: jest.fn(),
    },
  },
}));

jest.mock('react-leaflet', () => ({
  useMap: () => ({ getContainer: () => global.document.body }),
  Circle: ({ children }: any) => <div data-testid="live-circle">{children}</div>,
  CircleMarker: ({ children }: any) => <div data-testid="live-state-marker">{children}</div>,
  Polygon: ({ children }: any) => <div data-testid="live-polygon">{children}</div>,
  Popup: ({ children }: any) => <div>{children}</div>,
}));

jest.mock('../services/apiService', () => ({
  geofenceService: { getLiveState: jest.fn() },
}));

const mockedGetLiveState = geofenceService.getLiveState as jest.Mock;

const response = {
  data: {
    schema_version: 'geofence-live-state.v1',
    generated_at: '2026-11-10T16:00:00',
    refresh_after_seconds: 5,
    geofences: [{
      id: 7,
      public_id: 'fence-7',
      nome: 'Garagem principal',
      descricao: null,
      regra: 'forbidden',
      status: 'active',
      version: 1,
      geometry_type: 'circle',
      geometry_version: 1,
      active_assignments: 1,
      geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 300 },
      live_summary: {
        targets: 1, inside: 1, outside: 0, unknown: 0,
        violations: 1, active_episodes: 1,
      },
      targets: [{
        assignment_id: 11,
        target_type: 'vehicle',
        target_label: 'ABC1D23',
        subject_type: 'vehicle',
        subject_id: 21,
        subject_label: 'ABC1D23',
        stable_state: 'inside',
        pending_state: null,
        pending_samples: 0,
        policy_active: true,
        schedule_active: true,
        timezone_name: 'America/Sao_Paulo',
        effective_from: null,
        effective_to: null,
        schedules: [],
        dwell_threshold_seconds: 120,
        hysteresis_meters: 30,
        is_violation: true,
        active_episode: true,
        violation_episode_id: 'episode-7',
        violation_started_at: '2026-11-10T15:59:00',
        dwell_notified_at: null,
        last_evaluated_at: '2026-11-10T16:00:00',
        last_transition_at: '2026-11-10T15:59:00',
        last_source: 'tracker',
        last_position: {
          latitude: -23.55, longitude: -46.63,
          accuracy_m: 5, signed_distance_m: 42,
        },
      }],
    }],
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetLiveState.mockResolvedValue(response);
});

test('desenha cerca e mostra alvo, estado, agenda e episódio ao vivo', async () => {
  render(<GeofenceLiveLayer />);

  expect((await screen.findAllByText('Garagem principal')).length).toBeGreaterThan(0);
  expect(screen.getAllByText('Dentro · violação').length).toBeGreaterThan(0);
  expect(screen.getByText(/Agenda ativa/)).toBeInTheDocument();
  expect(screen.getByText('Episódio ativo')).toBeInTheDocument();
  expect(screen.getByTestId('live-circle')).toBeInTheDocument();
  expect(screen.getByTestId('live-state-marker')).toBeInTheDocument();
  expect(screen.getByText(/1 alvo\(s\) · 1 violação\(ões\)/)).toBeInTheDocument();
});

test('exibe vazio real sem inventar cercas', async () => {
  mockedGetLiveState.mockResolvedValue({
    data: { ...response.data, geofences: [] },
  });

  render(<GeofenceLiveLayer />);

  expect(await screen.findByText('Nenhuma cerca operacional cadastrada.')).toBeInTheDocument();
  expect(screen.queryByTestId('live-circle')).not.toBeInTheDocument();
});

test('mostra erro explícito e permite tentar novamente', async () => {
  mockedGetLiveState
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(response);

  render(<GeofenceLiveLayer />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Estado das cercas indisponível');
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
  await waitFor(() => expect(screen.getAllByText('Garagem principal').length).toBeGreaterThan(0));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
