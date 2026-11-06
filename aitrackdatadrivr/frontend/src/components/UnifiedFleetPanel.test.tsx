import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import UnifiedFleetPanel from './UnifiedFleetPanel';
import type { UnifiedFleetItem } from './UnifiedFleetPanel';

const items: UnifiedFleetItem[] = [
  {
    id: 'tracker:SIM-1000',
    source: 'tracker',
    primaryLabel: 'ABC-1D23',
    secondaryLabel: 'SIM-1000',
    score: 82.5,
    sourceId: 'SIM-1000',
  },
  {
    id: 'dirijabem:614',
    source: 'dirijabem',
    primaryLabel: 'Motorista Dirija Bem',
    secondaryLabel: 'Usuário 614',
    score: null,
    sourceId: 614,
  },
];

test('preserva a origem e não inventa score na visão unificada', () => {
  render(<UnifiedFleetPanel items={items} selectedItemId={null} onItemSelect={jest.fn()} />);

  expect(screen.getByText('ABC-1D23')).toBeInTheDocument();
  expect(screen.getByText('Motorista Dirija Bem')).toBeInTheDocument();
  expect(screen.getByText('Score 82.5')).toBeInTheDocument();
  expect(screen.getByText('Score indisponível')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Todos (2)' })).toHaveAttribute('aria-pressed', 'true');
});

test('filtra por fonte sem perder a opção de visão conjunta', () => {
  render(<UnifiedFleetPanel items={items} selectedItemId={null} onItemSelect={jest.fn()} />);

  fireEvent.click(screen.getByRole('button', { name: 'Tracker (1)' }));
  expect(screen.getByText('ABC-1D23')).toBeInTheDocument();
  expect(screen.queryByText('Motorista Dirija Bem')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Todos (2)' }));
  expect(screen.getByText('Motorista Dirija Bem')).toBeInTheDocument();
});

test('informa o item e sua fonte ao selecionar', () => {
  const onItemSelect = jest.fn();
  render(<UnifiedFleetPanel items={items} selectedItemId={null} onItemSelect={onItemSelect} />);

  fireEvent.click(screen.getByRole('button', { name: /Motorista Dirija Bem/ }));

  expect(onItemSelect).toHaveBeenCalledWith(items[1]);
});
