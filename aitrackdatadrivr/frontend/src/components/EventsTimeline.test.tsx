import React from 'react';
import axios from 'axios';
import { fireEvent, render, screen } from '@testing-library/react';
import EventsTimeline from './EventsTimeline';

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;
let consoleErrorSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  consoleErrorSpy.mockRestore();
});

test('diferencia resposta vazia de falha da timeline', async () => {
  mockedAxios.get.mockResolvedValue({ data: [] });

  render(<EventsTimeline onEventClick={jest.fn()} />);

  expect(await screen.findByText('Nenhum evento foi registrado no período consultado.')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('mostra erro e permite repetir a consulta', async () => {
  mockedAxios.get
    .mockRejectedValueOnce(new Error('API indisponível'))
    .mockResolvedValue({ data: [] });

  render(<EventsTimeline onEventClick={jest.fn()} />);

  fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }));

  expect(await screen.findByText('Nenhum evento foi registrado no período consultado.')).toBeInTheDocument();
  expect(mockedAxios.get).toHaveBeenCalledTimes(2);
});
