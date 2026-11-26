import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App';

vi.mock('./components/MapComponent', () => ({ default: () => <div data-testid="mapa" /> }));
vi.mock('./components/VehicleListUnified', () => ({ default: () => <div data-testid="frota" /> }));

test('renderiza a aplicação de rastreamento', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: 'AITrack - Monitoramento em Tempo Real' })).toBeInTheDocument();
  expect(screen.getByTestId('mapa')).toBeInTheDocument();
  expect(screen.getByTestId('frota')).toBeInTheDocument();
});
