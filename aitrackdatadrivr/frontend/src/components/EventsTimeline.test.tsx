import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import EventsTimeline from './EventsTimeline';
import { fleetService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  fleetService: {
    getEvents: jest.fn(),
  },
}));

const mockedGetEvents = fleetService.getEvents as jest.Mock;
let consoleErrorSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  consoleErrorSpy.mockRestore();
});

test('diferencia resposta vazia de falha da timeline', async () => {
  mockedGetEvents.mockResolvedValue({ data: [] });

  render(<EventsTimeline onEventClick={jest.fn()} />);

  expect(await screen.findByText('Nenhum evento foi registrado no período consultado.')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('mostra erro e permite repetir a consulta', async () => {
  mockedGetEvents
    .mockRejectedValueOnce(new Error('API indisponível'))
    .mockResolvedValue({ data: [] });

  render(<EventsTimeline onEventClick={jest.fn()} />);

  fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }));

  expect(await screen.findByText('Nenhum evento foi registrado no período consultado.')).toBeInTheDocument();
  expect(mockedGetEvents).toHaveBeenCalledTimes(2);
});

const recentEvents = [
  { device_id: 'SIM-1000', type: 'speeding', timestamp: new Date().toISOString(), severity: 'high', icon: '🚨', lat: -23.5, lon: -46.6, episode_id: 'ep-1' },
  { device_id: 'SIM-1001', type: 'harsh_brake', timestamp: new Date().toISOString(), severity: 'critical', icon: '🛑', lat: -23.5, lon: -46.6, episode_id: 'ep-2' },
  { device_id: 'SIM-1000', type: 'sharp_turn', timestamp: '2020-01-01T00:00:00Z', severity: 'medium', icon: '↪️', lat: -23.5, lon: -46.6, episode_id: 'ep-3' },
];

test('combina filtros de veículo, tipo e severidade', async () => {
  mockedGetEvents.mockResolvedValue({ data: recentEvents });
  render(<EventsTimeline onEventClick={jest.fn()} />);
  await screen.findByText('3 de 3 episódios exibidos');

  fireEvent.change(screen.getByRole('textbox', { name: 'Filtrar por veículo' }), { target: { value: '1001' } });
  fireEvent.change(screen.getByRole('combobox', { name: 'Filtrar por tipo' }), { target: { value: 'harsh_brake' } });
  fireEvent.change(screen.getByRole('combobox', { name: 'Filtrar por severidade' }), { target: { value: 'critical' } });

  expect(screen.getByText('1 de 3 episódios exibidos')).toBeInTheDocument();
  expect(screen.getByText('SIM-1001')).toBeInTheDocument();
  expect(screen.queryByText('SIM-1000')).not.toBeInTheDocument();
});

test('filtra por período e limpa todos os filtros', async () => {
  mockedGetEvents.mockResolvedValue({ data: recentEvents });
  render(<EventsTimeline onEventClick={jest.fn()} />);
  await screen.findByText('3 de 3 episódios exibidos');

  fireEvent.change(screen.getByRole('combobox', { name: 'Filtrar por período' }), { target: { value: '1h' } });
  expect(screen.getByText('2 de 3 episódios exibidos')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Limpar filtros' }));

  expect(screen.getByText('3 de 3 episódios exibidos')).toBeInTheDocument();
});

test('mantém o índice original ao selecionar resultado filtrado', async () => {
  const onEventClick = jest.fn();
  mockedGetEvents.mockResolvedValue({ data: recentEvents });
  render(<EventsTimeline onEventClick={onEventClick} />);
  await screen.findByText('3 de 3 episódios exibidos');
  fireEvent.change(screen.getByRole('textbox', { name: 'Filtrar por veículo' }), { target: { value: '1001' } });
  fireEvent.click(screen.getByRole('button', { name: 'Abrir episódio Frenagem Brusca de SIM-1001' }));

  expect(onEventClick).toHaveBeenCalledWith(1);
});
