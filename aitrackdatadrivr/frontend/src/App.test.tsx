import { vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';
import { runtimeEnvironmentService } from './services/apiService';
import { AuthContext } from './components/AuthGate';

const mockSelectedEpisode = {
  device_id: 'SIM-1001', type: 'harsh_brake', timestamp: '2026-11-06T12:00:00Z',
  severity: 'critical', icon: '🛑', lat: -23.51, lon: -46.61, episode_id: 'ep-test',
};

vi.mock('./components/MapComponent', () => ({ default: (props: any) => (
  <div
    data-testid="map"
    data-selected-vehicle={props.selectedVehicleId ?? ''}
    data-highlighted-event={props.highlightedEvent?.episode_id ?? ''}
  />
)}));
vi.mock('./components/BehavioralDashboard', () => ({ default: () => <div data-testid="dashboard" /> }));
vi.mock('./components/EventsTimeline', () => ({ default: (props: any) => (
  <button type="button" onClick={() => props.onEventClick(mockSelectedEpisode)}>Selecionar episódio de teste</button>
)}));
vi.mock('./components/VehicleAnalytics', () => ({ default: () => <div /> }));
vi.mock('./components/MonitorDashboard', () => ({ default: () => <div /> }));
vi.mock('./components/MonitorDetailView', () => ({ default: () => <div /> }));
vi.mock('./components/AgentConfigurationPanel', () => ({ default: () => <div>Configuração de agentes</div> }));
vi.mock('./components/AgentRunsPanel', () => ({ default: () => <div>Execuções de agentes</div> }));
vi.mock('./components/InternalNotificationsPanel', () => ({ default: () => <div>Notificações internas</div> }));
vi.mock('./components/HealthIntegrationsPanel', () => ({ default: () => <div>Painel de saúde</div> }));
vi.mock('./components/AlertsPanel', () => ({ default: () => <div /> }));
vi.mock('./components/EventsCatalog', () => ({ default: () => <div /> }));
vi.mock('./components/VehicleDetailHeader', () => ({ default: (props: any) => (
  props.selectedVehicleId
    ? <button type="button" onClick={props.onClear}>Fechar contexto de teste</button>
    : null
)}));
vi.mock('./components/VehicleSensorsPanel', () => ({ default: (props: any) => (
  <div data-testid="sensors" data-selected-vehicle={props.selectedVehicleId ?? ''} />
)}));
vi.mock('./services/apiService', () => ({
  runtimeEnvironmentService: { getCurrent: vi.fn() },
}));

const mockedGetCurrent = runtimeEnvironmentService.getCurrent as jest.Mock;

beforeEach(() => {
  mockedGetCurrent.mockResolvedValue({ data: {
    schema_version: 'runtime-environment.v1',
    generated_at: new Date().toISOString(),
    mode: 'simulation', authority: 'test', safe_for_real_actions: false, issues: [],
    sources: [
      { source: 'tracker', label: 'Tracker', mode: 'simulation', configured: true },
      { source: 'dirijabem', label: 'Dirija Bem', mode: 'simulation', configured: true },
    ],
  } });
});

test('renderiza a marca e mostra o modo confirmado pelo backend', async () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument();
  expect(await screen.findByRole('status', { name: 'Ambiente: SIMULAÇÃO' })).toBeInTheDocument();
});

test('drill-down entrega identidade e posição exatas do episódio ao mapa', async () => {
  render(<App />);
  await screen.findByRole('status', { name: 'Ambiente: SIMULAÇÃO' });
  fireEvent.click(screen.getByRole('button', { name: /Timeline/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Selecionar episódio de teste' }));

  expect(screen.getByTestId('map')).toHaveAttribute('data-selected-vehicle', 'SIM-1001');
  expect(screen.getByTestId('map')).toHaveAttribute('data-highlighted-event', 'ep-test');
  fireEvent.click(screen.getByRole('tab', { name: 'Sensores' }));
  expect(screen.getByTestId('sensors')).toHaveAttribute('data-selected-vehicle', 'SIM-1001');
  fireEvent.click(screen.getByRole('tab', { name: 'Mapa e rota' }));
  expect(screen.getByTestId('map')).toHaveAttribute('data-selected-vehicle', 'SIM-1001');
  fireEvent.click(screen.getByRole('button', { name: 'Fechar contexto de teste' }));
  expect(screen.getByTestId('map')).toHaveAttribute('data-selected-vehicle', '');
  expect(screen.getByTestId('map')).toHaveAttribute('data-highlighted-event', '');
});

test('mostra a navegação de saúde somente para health.read', async () => {
  const session = {
    schema_version: 'auth-session.v1' as const,
    user: { public_id: 'user-test', email: 'auditor@example.test', display_name: 'Auditor' },
    tenant: { public_id: 'tenant-test', slug: 'tenant-teste' },
    roles: ['auditor'],
    permissions: ['health.read'],
    expires_at: '2026-11-25T20:00:00Z',
  };
  const { rerender } = render(<AuthContext.Provider value={session}><App /></AuthContext.Provider>);

  await screen.findByRole('status', { name: 'Ambiente: SIMULAÇÃO' });
  fireEvent.click(screen.getByRole('button', { name: /Saúde/ }));
  expect(screen.getByText('Painel de saúde')).toBeInTheDocument();

  rerender(<AuthContext.Provider value={{ ...session, permissions: [] }}><App /></AuthContext.Provider>);
  expect(screen.queryByRole('button', { name: /Saúde/ })).not.toBeInTheDocument();
});
