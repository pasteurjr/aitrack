import React from 'react';
import { render, screen } from '@testing-library/react';
import OperationModeBadge from './OperationModeBadge';
import { resolveOperationMode } from '../config/operationMode';

describe('resolveOperationMode', () => {
  it.each([
    ['simulation', 'simulation', 'SIMULAÇÃO'],
    ['replay', 'replay', 'REPLAY'],
    ['production', 'production', 'PRODUÇÃO'],
    [' produção ', 'production', 'PRODUÇÃO'],
  ])('resolve %s como %s', (value, expectedMode, expectedLabel) => {
    const result = resolveOperationMode(value);

    expect(result.mode).toBe(expectedMode);
    expect(result.label).toBe(expectedLabel);
  });

  it.each([undefined, '', 'valor-invalido'])(
    'usa simulação como fallback seguro para %s',
    (value) => {
      expect(resolveOperationMode(value).mode).toBe('simulation');
    },
  );
});

describe('OperationModeBadge', () => {
  it('expõe o modo de produção como status global acessível', () => {
    render(<OperationModeBadge modeValue="production" />);

    expect(screen.getByRole('status', { name: 'Ambiente: PRODUÇÃO' })).toHaveTextContent(
      'AMBIENTE: PRODUÇÃO',
    );
  });
});
