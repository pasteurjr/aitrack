import React from 'react';
import { render, screen } from '@testing-library/react';
import EventsCatalog from './EventsCatalog';
import MonitorDetailView from './MonitorDetailView';
import { eventService, monitorService } from '../services/apiService';

jest.mock('./MapComponent', () => () => <div data-testid="map" />);
jest.mock('../services/apiService', () => ({
  eventService: { getCatalog: jest.fn(), getStats: jest.fn(), getAll: jest.fn() },
  monitorService: { getVehicles: jest.fn() },
}));

const mockedEvents = eventService as jest.Mocked<typeof eventService>;
const mockedMonitors = monitorService as jest.Mocked<typeof monitorService>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedEvents.getCatalog.mockResolvedValue({ data: [{
    id: 1, codigo: 'speeding', nome: 'Excesso de Velocidade',
    categoria: 'behavioral', severidade_padrao: 'high', icone: '🚨',
    cor: '#ea580c', descricao: 'Acima do limite.',
  }] } as any);
  mockedEvents.getStats.mockResolvedValue({ data: {
    total_eventos_hoje: 3, por_tipo: { speeding: 3 }, por_categoria: { behavioral: 3 },
  } } as any);
  mockedEvents.getAll.mockResolvedValue({ data: [{
    id: 99, tipo_evento_codigo: 'speeding', tipo_evento_nome: 'Excesso de Velocidade',
    categoria: 'behavioral', severidade: 'high', device_id: 'SIM-1000',
    timestamp: '2026-11-10T17:30:00', latitude: -23.5, longitude: -46.6,
    velocidade: 85, dados_adicionais: null,
  }] } as any);
  mockedMonitors.getVehicles.mockResolvedValue({ data: [{ device_id: 'SIM-1000' }] } as any);
});

test('catálogo exibe tipos e contagens vindos das APIs', async () => {
  render(<EventsCatalog />);

  expect(await screen.findByText('Excesso de Velocidade')).toBeInTheDocument();
  expect(screen.getByText('3 hoje')).toBeInTheDocument();
  expect(screen.queryByText(/DEMONSTRAÇÃO/)).not.toBeInTheDocument();
});

test('detalhe do monitor filtra eventos persistidos pelos veículos atribuídos', async () => {
  render(<MonitorDetailView monitorId={1} selectedVehicle={null} />);

  expect(await screen.findByText('Excesso de Velocidade')).toBeInTheDocument();
  expect(screen.getByText('SIM-1000')).toBeInTheDocument();
  expect(mockedMonitors.getVehicles).toHaveBeenCalledWith(1);
  expect(mockedEvents.getAll).toHaveBeenCalledWith({ limit: 100, device_id: 'SIM-1000' });
  expect(screen.queryByText(/DEMONSTRAÇÃO/)).not.toBeInTheDocument();
});
