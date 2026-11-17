import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import VehicleSensorsPanel from './VehicleSensorsPanel';
import { detectorPolicyService, sensorService, unifiedVehicleService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  sensorService: { getByVehicle: jest.fn() },
  detectorPolicyService: { getAll: jest.fn(), activate: jest.fn() },
  unifiedVehicleService: { getAll: jest.fn() },
}));

const getFleet = unifiedVehicleService.getAll as jest.Mock;
const getSensors = sensorService.getByVehicle as jest.Mock;
const getPolicies = detectorPolicyService.getAll as jest.Mock;
const activatePolicy = detectorPolicyService.activate as jest.Mock;

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
    sources: ['tracker'], protocols: ['maxtrack'], commands: [
      { protocol_code: 'maxtrack', capability_code: 'remote_immobilization', support_status: 'unknown', evidence: 'Sem canal' },
    ], confirmed_commands: [], count: 2,
    sensors: [
      {
        id: 1, source_code: 'tracker', protocol_code: 'maxtrack', device_model: '*',
        external_device_id: 'SIM-1000', capability_code: 'ignition', unit: null,
        lifecycle_status: 'active', first_seen_at: '2026-11-17T15:00:00',
        last_seen_at: '2026-11-17T15:01:00', support_status: 'confirmed',
        evidence: 'parser', configured: true, health_status: 'current',
        latest_reading: {
          value: true, value_type: 'boolean', unit: null, quality: 'valid',
          observed_at: '2026-11-17T18:01:00', received_at: '2026-11-17T15:01:00-03:00',
          recorded_at: '2026-11-17T15:01:00-03:00', age_seconds: 2,
          clock_skew_seconds: 10800, observed_timezone: 'unspecified',
          received_timezone: 'America/Sao_Paulo',
        },
      },
      {
        id: 2, source_code: 'tracker', protocol_code: 'maxtrack', device_model: '*',
        external_device_id: 'SIM-1000', capability_code: 'external_voltage', unit: 'V',
        lifecycle_status: 'active', first_seen_at: '2026-11-17T15:00:00',
        last_seen_at: '2026-11-17T15:01:00', support_status: 'confirmed',
        evidence: 'parser', configured: true, health_status: 'stale',
        latest_reading: {
          value: 12.7, value_type: 'number', unit: 'V', quality: 'valid',
          observed_at: '2026-11-17T18:01:00', received_at: '2026-11-17T15:01:00-03:00',
          recorded_at: '2026-11-17T15:01:00-03:00', age_seconds: 180,
          clock_skew_seconds: 10800, observed_timezone: 'unspecified',
          received_timezone: 'America/Sao_Paulo',
        },
      },
    ],
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  getFleet.mockResolvedValue(fleet);
  getSensors.mockResolvedValue(sensors);
  getPolicies.mockResolvedValue({ data: { schema_version: 'detector-policies.v1', count: 0, policies: [] } });
  activatePolicy.mockResolvedValue({ data: {} });
});

test('mostra somente sensores observados vindos da API real', async () => {
  render(<VehicleSensorsPanel selectedVehicleId="SIM-1000" selectedUserId={null} />);

  expect(screen.getByRole('status')).toHaveAttribute('data-state', 'loading');
  expect(await screen.findByRole('heading', { name: 'Sensores do veículo' })).toBeInTheDocument();
  expect(screen.getByText('Ignição')).toBeInTheDocument();
  expect(screen.getByText('Tensão externa')).toBeInTheDocument();
  expect(screen.getByText('Ligado / verdadeiro')).toBeInTheDocument();
  expect(screen.getByText('12.7 V')).toBeInTheDocument();
  expect(screen.getByText('DESATUALIZADO')).toBeInTheDocument();
  expect(screen.getAllByText('SUPORTE CONFIRMADO')).toHaveLength(2);
  expect(screen.getByText(/Nenhum comando físico confirmado/)).toBeInTheDocument();
  expect(screen.getAllByText('Detecção não configurada')).toHaveLength(2);
  expect(getSensors).toHaveBeenCalledWith(12);
});

test('ativa política operacional com autoria sem oferecer comando físico', async () => {
  const draft = {
    id: 7, policy_key: 'ignition-watch', version_number: 2,
    detector_type: 'state', capability_code: 'ignition', scope_type: 'vehicle',
    scope_ref: '12', parameters: { expected: true }, status: 'draft',
  };
  const active = { ...draft, status: 'active' };
  getPolicies
    .mockResolvedValueOnce({ data: { schema_version: 'detector-policies.v1', count: 1, policies: [draft] } })
    .mockResolvedValueOnce({ data: { schema_version: 'detector-policies.v1', count: 1, policies: [active] } });
  render(<VehicleSensorsPanel selectedVehicleId="SIM-1000" selectedUserId={null} />);

  expect(await screen.findByText('Ativar detecção — política v2')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Operador da ativação'), { target: { value: 'operador-1' } });
  fireEvent.change(screen.getByLabelText('Motivo da ativação'), { target: { value: 'Homologação operacional' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ativar política de detecção' }));

  await waitFor(() => expect(activatePolicy).toHaveBeenCalledWith(7, {
    actor: 'operador-1', reason: 'Homologação operacional',
    correlation_id: 'ui:vehicle:12:policy:7',
  }));
  expect(await screen.findByText('Detecção operacional ativa')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /bloqueio|acionamento/i })).not.toBeInTheDocument();
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
