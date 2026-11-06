import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('./components/MapComponent', () => () => <div data-testid="map" />);
jest.mock('./components/BehavioralDashboard', () => () => <div data-testid="dashboard" />);
jest.mock('./components/EventsTimeline', () => () => <div />);
jest.mock('./components/VehicleAnalytics', () => () => <div />);
jest.mock('./components/MonitorDashboard', () => () => <div />);
jest.mock('./components/MonitorDetailView', () => () => <div />);
jest.mock('./components/AlertsPanel', () => () => <div />);
jest.mock('./components/EventsCatalog', () => () => <div />);
jest.mock('./components/VehicleDetailHeader', () => () => <div />);

test('renderiza a marca e assume simulação quando o modo não está configurado', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: 'AITrack + DataDrivr' })).toBeInTheDocument();
  expect(screen.getByRole('status', { name: 'Ambiente: SIMULAÇÃO' })).toBeInTheDocument();
});
