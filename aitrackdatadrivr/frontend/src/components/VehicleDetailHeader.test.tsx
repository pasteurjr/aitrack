import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import VehicleDetailHeader from './VehicleDetailHeader';
import { unifiedVehicleService } from '../services/apiService';
import type { UnifiedVehicleDTO } from '../types/unifiedVehicle';

jest.mock('../services/apiService', () => ({
  unifiedVehicleService: { getAll: jest.fn() },
}));

const getAll = unifiedVehicleService.getAll as jest.MockedFunction<typeof unifiedVehicleService.getAll>;

const trackerVehicle: UnifiedVehicleDTO = {
  schema_version: 'vehicle.v1',
  vehicle_id: 1000,
  identity_type: 'tracker_only',
  display_name: 'Veículo simulado rastreador GPS 1',
  plate: 'ABC1D23',
  active: true,
  tracker: { device_id: 'SIM-1000', veicod: 1000 },
  dirijabem: null,
  telemetry: [{
    source: 'tracker',
    mode: 'simulation',
    last_communication_at: '2026-11-06T12:30:00Z',
  }],
};

beforeEach(() => {
  getAll.mockReset();
});

test('não consulta nem renderiza sem seleção', () => {
  const { container } = render(
    <VehicleDetailHeader selectedVehicleId={null} selectedUserId={null} onClear={jest.fn()} />,
  );

  expect(container).toBeEmptyDOMElement();
  expect(getAll).not.toHaveBeenCalled();
});

test('resolve a seleção Tracker e mostra apenas metadados reais', async () => {
  getAll.mockResolvedValue({ data: { contract: 'vehicle-list.v1', count: 1, vehicles: [trackerVehicle] } } as never);

  render(<VehicleDetailHeader selectedVehicleId="SIM-1000" selectedUserId={null} onClear={jest.fn()} />);

  expect(await screen.findByRole('heading', { name: trackerVehicle.display_name })).toBeInTheDocument();
  expect(screen.getByText(/ABC1D23 · SIM-1000/)).toBeInTheDocument();
  expect(screen.getByText('TRACKER')).toBeInTheDocument();
  expect(screen.getByText('Modo: simulation')).toBeInTheDocument();
  expect(screen.getByText(/Último contato:/)).not.toHaveTextContent('não informado');
  expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
});

test('explicita quando a identidade selecionada não está vinculada', async () => {
  getAll.mockResolvedValue({ data: { contract: 'vehicle-list.v1', count: 0, vehicles: [] } } as never);

  render(<VehicleDetailHeader selectedVehicleId="DESCONHECIDO" selectedUserId={null} onClear={jest.fn()} />);

  expect(await screen.findByText('Identidade não vinculada ao cadastro unificado')).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'DESCONHECIDO' })).toBeInTheDocument();
});

test('fecha o contexto por ação explícita', async () => {
  const onClear = jest.fn();
  getAll.mockResolvedValue({ data: { contract: 'vehicle-list.v1', count: 1, vehicles: [trackerVehicle] } } as never);

  render(<VehicleDetailHeader selectedVehicleId="SIM-1000" selectedUserId={null} onClear={onClear} />);
  await screen.findByRole('heading', { name: trackerVehicle.display_name });
  fireEvent.click(screen.getByRole('button', { name: 'Fechar detalhe do veículo' }));

  expect(onClear).toHaveBeenCalledTimes(1);
});

test('mostra indisponibilidade sem inventar cadastro quando a API falha', async () => {
  const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
  getAll.mockRejectedValue(new Error('offline'));

  render(<VehicleDetailHeader selectedVehicleId={null} selectedUserId={614} onClear={jest.fn()} />);

  await waitFor(() => expect(screen.getByText('Identidade indisponível')).toBeInTheDocument());
  expect(screen.getByRole('heading', { name: 'Usuário Dirija Bem 614' })).toBeInTheDocument();
  consoleError.mockRestore();
});
