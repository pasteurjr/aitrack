import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import VehicleSensorsPanel from './VehicleSensorsPanel';
import { sensorService, unifiedVehicleService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  sensorService: { getByVehicle: jest.fn() },
  unifiedVehicleService: { getAll: jest.fn() },
}));

const getFleet = unifiedVehicleService.getAll as jest.Mock;
const getSensors = sensorService.getByVehicle as jest.Mock;

const fleet = {
  data: {
    vehicles: [{
      vehicle_id: 12,
      tracker: { device_id: 'SIM-1000', veicod: 1000 },
      dirijabem: null,
    }],
  },
};

const sensors = {
  data: {
    schema_version: 'vehicle-sensors.v1',
    vehicle: { id: 12, public_id: 'vehicle-12', plate: 'SIM1000', active: true },
    sources: ['tracker'], protocols: ['maxtrack'], count: 2,
    sensors: [
      {
        id: 1, source_code: 'tracker', protocol_code: 'maxtrack', device_model: '*',
        external_device_id: 'SIM-1000', capability_code: 'ignition', unit: null,
        lifecycle_status: 'active', first_seen_at: '2026-11-17T15:00:00',
        last_seen_at: '2026-11-17T15:01:00', support_status: 'confirmed',
        evidence: 'parser', configured: true,
      },
      {
        id: 2, source_code: 'tracker', protocol_code: 'maxtrack', device_model: '*',
        external_device_id: 'SIM-1000', capability_code: 'external_voltage', unit: 'V',
        lifecycle_status: 'active', first_seen_at: '2026-11-17T15:00:00',
        last_seen_at: '2026-11-17T15:01:00', support_status: 'confirmed',
        evidence: 'parser', configured: true,
      },
    ],
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  getFleet.mockResolvedValue(fleet);
  getSensors.mockResolvedValue(sensors);
});

test('mostra somente sensores observados vindos da API real', async () => {
  render(<VehicleSensorsPanel selectedVehicleId="SIM-1000" selectedUserId={null} />);

  expect(screen.getByRole('status')).toHaveAttribute('data-state', 'loading');
  expect(await screen.findByRole('heading', { name: 'Sensores do veículo' })).toBeInTheDocument();
  expect(screen.getByText('Ignição')).toBeInTheDocument();
  expect(screen.getByText('Tensão externa')).toBeInTheDocument();
  expect(screen.getAllByText('SUPORTE CONFIRMADO')).toHaveLength(2);
  expect(getSensors).toHaveBeenCalledWith(12);
});

test('vazio não transforma evento Dirija Bem em sensor físico', async () => {
  getSensors.mockResolvedValue({ data: { ...sensors.data, count: 0, sensors: [], sources: [], protocols: [] } });
  render(<VehicleSensorsPanel selectedVehicleId="SIM-1000" selectedUserId={null} />);

  expect(await screen.findByText('Nenhum sensor físico observado')).toBeInTheDocument();
  expect(screen.getByText(/Eventos do Dirija Bem não são convertidos/)).toBeInTheDocument();
});

test('falha é explícita e permite tentar novamente', async () => {
  const consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
  getSensors.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(sensors);
  render(<VehicleSensorsPanel selectedVehicleId="SIM-1000" selectedUserId={null} />);

  expect(await screen.findByRole('alert')).toHaveAttribute('data-state', 'error');
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
  await waitFor(() => expect(getSensors).toHaveBeenCalledTimes(2));
  expect(await screen.findByText('Ignição')).toBeInTheDocument();
  consoleError.mockRestore();
});
