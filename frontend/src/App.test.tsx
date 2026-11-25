import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('./components/MapComponent', () => () => <div data-testid="mapa" />);
jest.mock('./components/VehicleListUnified', () => () => <div data-testid="frota" />);

test('renderiza a aplicação de rastreamento', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: 'AITrack - Monitoramento em Tempo Real' })).toBeInTheDocument();
  expect(screen.getByTestId('mapa')).toBeInTheDocument();
  expect(screen.getByTestId('frota')).toBeInTheDocument();
});
