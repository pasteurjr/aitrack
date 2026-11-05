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
