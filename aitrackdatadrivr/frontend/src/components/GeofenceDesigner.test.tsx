import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import GeofenceDesigner, { draftToApiGeometry } from './GeofenceDesigner';
import { geofenceService } from '../services/apiService';

let mockMapHandlers: Record<string, (event: any) => void> = {};
const mockDoubleClickZoom = {
  enabled: jest.fn(() => true),
  disable: jest.fn(),
  enable: jest.fn(),
};
const mockMap = {
  getContainer: () => document.body,
  distance: jest.fn(() => 250),
  doubleClickZoom: mockDoubleClickZoom,
};

jest.mock('leaflet', () => ({
  __esModule: true,
  default: {
    DomEvent: {
      disableClickPropagation: jest.fn(),
      disableScrollPropagation: jest.fn(),
    },
  },
}));

jest.mock('react-leaflet', () => ({
  useMap: () => mockMap,
  useMapEvents: (handlers: Record<string, (event: any) => void>) => {
    mockMapHandlers = handlers;
    return mockMap;
  },
  Circle: ({ children }: any) => <div data-testid="map-circle">{children}</div>,
  CircleMarker: () => <div data-testid="map-vertex" />,
  Polygon: ({ children }: any) => <div data-testid="map-polygon">{children}</div>,
  Polyline: () => <div data-testid="map-polyline" />,
  Popup: ({ children }: any) => <div>{children}</div>,
}));

jest.mock('../services/apiService', () => ({
  geofenceService: {
    getAll: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    archive: jest.fn(),
    getAssignmentOptions: jest.fn(),
    getAssignments: jest.fn(),
    assign: jest.fn(),
    updateAssignment: jest.fn(),
    deactivateAssignment: jest.fn(),
    createGroup: jest.fn(),
  },
}));

const mockedService = geofenceService as jest.Mocked<typeof geofenceService>;

beforeEach(() => {
  window.localStorage.clear();
  mockMapHandlers = {};
  jest.clearAllMocks();
  mockMap.distance.mockReturnValue(250);
  mockDoubleClickZoom.enabled.mockReturnValue(true);
  mockedService.getAll.mockResolvedValue({
    data: { schema_version: 'geofence-list.v1', total: 0, limit: 200, offset: 0, geofences: [] },
  } as any);
  mockedService.create.mockResolvedValue({
    data: {
      schema_version: 'geofence-detail.v1',
      geofence: {
        id: 7,
        public_id: 'fence-7',
        nome: 'Área de teste',
        descricao: null,
        regra: 'forbidden',
        status: 'draft',
        version: 1,
        geometry_type: 'polygon',
        geometry_version: 1,
        active_assignments: 0,
        geometry: {
          type: 'Polygon',
          coordinates: [[[-46.6, -23.5], [-46.61, -23.51], [-46.62, -23.5], [-46.6, -23.5]]],
        },
      },
    },
  } as any);
  mockedService.update.mockResolvedValue({
    data: {
      schema_version: 'geofence-detail.v1',
      geofence: {
        id: 7, public_id: 'fence-7', nome: 'Área atualizada', descricao: null,
        regra: 'allowed', status: 'active', version: 2, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 0,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      },
    },
  } as any);
  mockedService.archive.mockResolvedValue({
    data: {
      schema_version: 'geofence-detail.v1',
      geofence: {
        id: 7, public_id: 'fence-7', nome: 'Área atualizada', descricao: null,
        regra: 'allowed', status: 'archived', version: 3, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 0,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      },
    },
  } as any);
  mockedService.getAssignmentOptions.mockResolvedValue({
    data: {
      schema_version: 'geofence-assignment-options.v1',
      vehicles: [{ id: 11, public_id: 'vehicle-11', label: 'ABC1D23' }],
      drivers: [{ id: 21, public_id: 'driver-21', label: 'João' }],
      groups: [],
    },
  } as any);
  mockedService.getAssignments.mockResolvedValue({
    data: { schema_version: 'geofence-assignments.v1', assignments: [] },
  } as any);
  mockedService.assign.mockResolvedValue({
    data: {
      schema_version: 'geofence-assignment.v1',
      assignment: {
        id: 31, geofence_id: 7, target_type: 'vehicle', target_label: 'ABC1D23',
        vehicle_id: 11, driver_id: null, group_id: null, notify_on_entry: false,
        notify_on_exit: true, ativo: true, version: 1,
        timezone_name: 'America/Sao_Paulo', effective_from: null, effective_to: null,
        dwell_threshold_seconds: null, hysteresis_meters: 30, schedules: [],
      },
    },
  } as any);
});

test('converte círculo da ordem Leaflet para longitude e latitude da API', () => {
  expect(draftToApiGeometry({
    type: 'circle', center: [-23.5505, -46.6333], radius: 499.999,
  })).toEqual({
    type: 'Circle', center: [-46.6333, -23.5505], radius_meters: 500,
  });
});

test('desenha polígono com mouse, fecha o anel e salva pela API', async () => {
  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('0 cadastrada(s)');
  fireEvent.click(screen.getByRole('button', { name: /polígono/i }));

  act(() => {
    mockMapHandlers.click({ latlng: { lat: -23.5, lng: -46.6 } });
    mockMapHandlers.click({ latlng: { lat: -23.51, lng: -46.61 } });
    mockMapHandlers.click({ latlng: { lat: -23.5, lng: -46.62 } });
  });

  expect(screen.getByText('3 vértice(s) marcado(s)')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /concluir polígono/i }));
  fireEvent.change(screen.getByLabelText('Nome da cerca'), { target: { value: 'Área de teste' } });
  fireEvent.change(screen.getByLabelText('Tipo de proteção da cerca'), { target: { value: 'forbidden' } });
  fireEvent.change(screen.getByLabelText('Operador responsável pela cerca'), { target: { value: 'Maria Operadora' } });
  fireEvent.click(screen.getByRole('button', { name: /salvar cerca/i }));

  await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
  expect(mockedService.create).toHaveBeenCalledWith(expect.objectContaining({
    nome: 'Área de teste',
    regra: 'forbidden',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [-46.6, -23.5], [-46.61, -23.51], [-46.62, -23.5], [-46.6, -23.5],
      ]],
    },
    operator: expect.objectContaining({ name: 'Maria Operadora' }),
  }));
  expect(await screen.findByText(/salva com sucesso/i)).toBeInTheDocument();
});

test('círculo usa dois cliques e exibe a prévia antes de salvar', async () => {
  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('0 cadastrada(s)');
  fireEvent.click(screen.getByRole('button', { name: /círculo/i }));

  act(() => mockMapHandlers.click({ latlng: { lat: -23.55, lng: -46.63 } }));
  act(() => mockMapHandlers.click({ latlng: { lat: -23.551, lng: -46.631 } }));

  expect(screen.getByText('Raio: 250 m')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /salvar cerca/i })).toBeEnabled();
  expect(screen.getByTestId('map-circle')).toBeInTheDocument();
});

test('edita cerca existente com versão esperada e motivo auditável', async () => {
  mockedService.getAll.mockResolvedValue({
    data: {
      schema_version: 'geofence-list.v1', total: 1, limit: 200, offset: 0,
      geofences: [{
        id: 7, public_id: 'fence-7', nome: 'Área antiga', descricao: null,
        regra: 'allowed', status: 'active', version: 1, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 0,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      }],
    },
  } as any);
  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('1 cadastrada(s)');
  fireEvent.change(screen.getByLabelText('Gerenciar cerca existente'), { target: { value: 'fence-7' } });
  fireEvent.change(screen.getByLabelText('Nome da cerca'), { target: { value: 'Área atualizada' } });
  fireEvent.change(screen.getByLabelText('Operador responsável pela cerca'), { target: { value: 'Maria' } });
  fireEvent.change(screen.getByLabelText('Motivo da alteração da cerca'), { target: { value: 'Ajuste cadastral' } });
  fireEvent.click(screen.getByRole('button', { name: /salvar alterações/i }));

  await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
  expect(mockedService.update).toHaveBeenCalledWith('fence-7', expect.objectContaining({
    expected_version: 1,
    change_reason: 'Ajuste cadastral',
    geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
  }));
});

test('arquiva sem apagar e exige confirmação do operador', async () => {
  mockedService.getAll.mockResolvedValue({
    data: {
      schema_version: 'geofence-list.v1', total: 1, limit: 200, offset: 0,
      geofences: [{
        id: 7, public_id: 'fence-7', nome: 'Área antiga', descricao: null,
        regra: 'allowed', status: 'inactive', version: 2, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 0,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      }],
    },
  } as any);
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('1 cadastrada(s)');
  fireEvent.change(screen.getByLabelText('Gerenciar cerca existente'), { target: { value: 'fence-7' } });
  fireEvent.change(screen.getByLabelText('Operador responsável pela cerca'), { target: { value: 'Maria' } });
  fireEvent.change(screen.getByLabelText('Motivo da alteração da cerca'), { target: { value: 'Área desativada' } });
  fireEvent.click(screen.getByRole('button', { name: 'Arquivar' }));

  await waitFor(() => expect(mockedService.archive).toHaveBeenCalledTimes(1));
  expect(mockedService.archive).toHaveBeenCalledWith('fence-7', expect.objectContaining({
    expected_version: 2, change_reason: 'Área desativada',
  }));
  expect(await screen.findByText(/histórico foi preservado/i)).toBeInTheDocument();
});

test('atribui veículo canônico e atualiza a contagem da cerca', async () => {
  mockedService.getAll.mockResolvedValue({
    data: {
      schema_version: 'geofence-list.v1', total: 1, limit: 200, offset: 0,
      geofences: [{
        id: 7, public_id: 'fence-7', nome: 'Garagem', descricao: null,
        regra: 'allowed', status: 'active', version: 1, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 0,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      }],
    },
  } as any);
  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('1 cadastrada(s)');
  fireEvent.change(screen.getByLabelText('Gerenciar cerca existente'), { target: { value: 'fence-7' } });
  await screen.findByText('Nenhum alvo atribuído.');
  fireEvent.change(screen.getByLabelText('Operador responsável pela cerca'), { target: { value: 'Maria' } });
  fireEvent.change(screen.getByLabelText('Alvo da cerca'), { target: { value: '11' } });
  fireEvent.click(screen.getByRole('button', { name: 'Atribuir alvo' }));

  await waitFor(() => expect(mockedService.assign).toHaveBeenCalledWith('fence-7', {
    target_type: 'vehicle', target_id: 11,
    operator: expect.objectContaining({ name: 'Maria' }),
  }));
  expect((await screen.findAllByText('ABC1D23')).length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText(/1 atribuição\(ões\) ativa\(s\)/)).toBeInTheDocument();
});

test('configura fuso, permanência e múltiplas janelas semanais da atribuição', async () => {
  const assignment = {
    id: 31, geofence_id: 7, target_type: 'vehicle', target_label: 'ABC1D23',
    vehicle_id: 11, driver_id: null, group_id: null, notify_on_entry: false,
    notify_on_exit: true, ativo: true, version: 3,
    timezone_name: 'America/Sao_Paulo', effective_from: null, effective_to: null,
    dwell_threshold_seconds: 900, hysteresis_meters: 30,
    schedules: [{
      id: 91, day_of_week: 4, start_time: '22:00:00', end_time: '06:00:00',
      crosses_midnight: true, ativo: true,
    }],
  };
  mockedService.getAll.mockResolvedValue({
    data: {
      schema_version: 'geofence-list.v1', total: 1, limit: 200, offset: 0,
      geofences: [{
        id: 7, public_id: 'fence-7', nome: 'Garagem', descricao: null,
        regra: 'allowed', status: 'active', version: 1, geometry_type: 'circle',
        geometry_version: 1, active_assignments: 1,
        geometry: { type: 'Circle', center: [-46.63, -23.55], radius_meters: 500 },
      }],
    },
  } as any);
  mockedService.getAssignments.mockResolvedValue({
    data: { schema_version: 'geofence-assignments.v1', assignments: [assignment] },
  } as any);
  mockedService.updateAssignment.mockResolvedValue({
    data: {
      schema_version: 'geofence-assignment.v1',
      assignment: {
        ...assignment, version: 4, timezone_name: 'America/Manaus',
        dwell_threshold_seconds: 1800,
      },
    },
  } as any);

  render(<GeofenceDesigner />);
  fireEvent.click(screen.getByRole('button', { name: /criar cerca/i }));
  await screen.findByText('1 cadastrada(s)');
  fireEvent.change(screen.getByLabelText('Gerenciar cerca existente'), { target: { value: 'fence-7' } });
  expect(await screen.findByText(/Sex 22:00–06:00 \(\+1 dia\)/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Operador responsável pela cerca'), { target: { value: 'Maria' } });
  fireEvent.click(screen.getByRole('button', { name: 'Configurar' }));
  fireEvent.change(screen.getByLabelText('Fuso horário da atribuição'), { target: { value: 'America/Manaus' } });
  fireEvent.change(screen.getByLabelText('Permanência em minutos'), { target: { value: '30' } });
  fireEvent.click(screen.getByRole('button', { name: 'Adicionar janela' }));
  fireEvent.change(screen.getByLabelText('Dia da janela 2'), { target: { value: '6' } });
  fireEvent.change(screen.getByLabelText('Início da janela 2'), { target: { value: '08:30' } });
  fireEvent.change(screen.getByLabelText('Fim da janela 2'), { target: { value: '12:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Salvar configuração' }));

  await waitFor(() => expect(mockedService.updateAssignment).toHaveBeenCalledWith('fence-7', 31, {
    expected_version: 3,
    timezone_name: 'America/Manaus',
    dwell_threshold_seconds: 1800,
    schedules: [
      { day_of_week: 4, start_time: '22:00:00', end_time: '06:00:00', crosses_midnight: true },
      { day_of_week: 6, start_time: '08:30:00', end_time: '12:00:00', crosses_midnight: false },
    ],
    operator: expect.objectContaining({ name: 'Maria' }),
  }));
  expect(await screen.findByText('Agenda da atribuição atualizada.')).toBeInTheDocument();
});
