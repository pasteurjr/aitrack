import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import MonitorDashboard from './MonitorDashboard';
import { monitorService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  monitorService: {
    getAll: jest.fn(),
    getById: jest.fn(),
    getVehicles: jest.fn(),
  },
}));

const mockedMonitorService = monitorService as jest.Mocked<typeof monitorService>;
let consoleErrorSpy: jest.SpyInstance;

const monitor = {
  id: 1,
  nome: 'Monitor real',
  descricao: 'Monitor de teste',
  tipo_monitor: 'safety' as const,
  ativo: true,
  intervalo_analise: 300,
  janela_contexto: 1800,
  eventos_minimos: 3,
  score_threshold: 70,
  gera_alertas: true,
  veiculos_monitorados: 1,
  criado_em: '2026-11-05T10:00:00',
};

beforeEach(() => {
  jest.clearAllMocks();
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
  mockedMonitorService.getAll.mockResolvedValue({ data: [monitor] } as any);
});

afterEach(() => {
  consoleErrorSpy.mockRestore();
});

test('mostra erro explícito quando os detalhes não podem ser consultados', async () => {
  mockedMonitorService.getById.mockRejectedValue(new Error('indisponível'));
  mockedMonitorService.getVehicles.mockRejectedValue(new Error('indisponível'));

  render(
    <MonitorDashboard
      selectedMonitorId={1}
      onMonitorSelect={jest.fn()}
      onVehicleSelect={jest.fn()}
    />,
  );

  expect(await screen.findByRole('alert')).toHaveTextContent('Informação indisponível');
  expect(screen.getByRole('alert')).toHaveTextContent('Scores, eventos e estados não foram inventados');
  expect(screen.queryByText(/Score: 85/)).not.toBeInTheDocument();
});

test('permite tentar novamente após falha dos detalhes', async () => {
  mockedMonitorService.getById
    .mockRejectedValueOnce(new Error('indisponível'))
    .mockResolvedValue({ data: monitor } as any);
  mockedMonitorService.getVehicles
    .mockRejectedValueOnce(new Error('indisponível'))
    .mockResolvedValue({ data: [] } as any);

  render(
    <MonitorDashboard
      selectedMonitorId={1}
      onMonitorSelect={jest.fn()}
      onVehicleSelect={jest.fn()}
    />,
  );

  fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }));

  await waitFor(() => expect(screen.getByText('Monitor real')).toBeInTheDocument());
  expect(mockedMonitorService.getVehicles).toHaveBeenCalledTimes(2);
});
