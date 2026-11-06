import { isUnifiedVehicleDTO, UNIFIED_VEHICLE_SCHEMA_VERSION } from './unifiedVehicle';

const trackerVehicle = {
  schema_version: UNIFIED_VEHICLE_SCHEMA_VERSION,
  vehicle_id: 10,
  identity_type: 'tracker_only',
  display_name: 'Veículo 10',
  plate: 'ABC-1D23',
  active: true,
  tracker: { device_id: 'SIM-1000', veicod: 42 },
  dirijabem: null,
};

test('aceita DTO coerente com a identidade declarada', () => {
  expect(isUnifiedVehicleDTO(trackerVehicle)).toBe(true);
});

test('rejeita versão desconhecida e fontes incoerentes', () => {
  expect(isUnifiedVehicleDTO({ ...trackerVehicle, schema_version: 'vehicle.v2' })).toBe(false);
  expect(isUnifiedVehicleDTO({ ...trackerVehicle, dirijabem: { codusu: 1 } })).toBe(false);
});
