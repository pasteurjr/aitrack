import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';
import { runtimeEnvironmentService } from './services/apiService';

const mockSelectedEpisode = {
  device_id: 'SIM-1001', type: 'harsh_brake', timestamp: '2026-11-06T12:00:00Z',
  severity: 'critical', icon: '🛑', lat: -23.51, lon: -46.61, episode_id: 'ep-test',
};

jest.mock('./components/MapComponent', () => (props: any) => (
  <div
    data-testid="map"
    data-selected-vehicle={props.selectedVehicleId ?? ''}
    data-highlighted-event={props.highlightedEvent?.episode_id ?? ''}
  />
));
jest.mock('./components/BehavioralDashboard', () => () => <div data-testid="dashboard" />);
jest.mock('./components/EventsTimeline', () => (props: any) => (
  <button type="button" onClick={() => props.onEventClick(mockSelectedEpisode)}>Selecionar episódio de teste</button>
));
jest.mock('./components/VehicleAnalytics', () => () => <div />);
jest.mock('./components/MonitorDashboard', () => () => <div />);
jest.mock('./components/MonitorDetailView', () => () => <div />);
jest.mock('./components/AlertsPanel', () => () => <div />);
jest.mock('./components/EventsCatalog', () => () => <div />);
jest.mock('./components/VehicleDetailHeader', () => (props: any) => (
  props.selectedVehicleId
    ? <button type="button" onClick={props.onClear}>Fechar contexto de teste</button>
    : null
));
jest.mock('./services/apiService', () => ({
  runtimeEnvironmentService: { getCurrent: jest.fn() },
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
  fireEvent.click(screen.getByRole('button', { name: 'Fechar contexto de teste' }));
  expect(screen.getByTestId('map')).toHaveAttribute('data-selected-vehicle', '');
  expect(screen.getByTestId('map')).toHaveAttribute('data-highlighted-event', '');
});
