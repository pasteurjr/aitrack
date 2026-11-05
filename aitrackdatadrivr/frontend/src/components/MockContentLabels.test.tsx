import React from 'react';
import { render, screen } from '@testing-library/react';
import AlertsPanel from './AlertsPanel';
import EventsCatalog from './EventsCatalog';
import MonitorDetailView from './MonitorDetailView';

jest.mock('./MapComponent', () => () => <div data-testid="map" />);

describe('identificação de conteúdo mock', () => {
  it.each([
    ['Alertas', <AlertsPanel />],
    ['Catálogo de Eventos', <EventsCatalog />],
    [
      'Detalhe do Monitor',
      <MonitorDetailView monitorId={1} vehicles={[]} selectedVehicle={null} />,
    ],
  ])('marca %s como demonstração não operacional', (_name, component) => {
    render(component);

    expect(screen.getByRole('note', { name: 'Conteúdo de demonstração' })).toHaveTextContent(
      'DEMONSTRAÇÃO — DADOS NÃO OPERACIONAIS',
    );
  });
});
