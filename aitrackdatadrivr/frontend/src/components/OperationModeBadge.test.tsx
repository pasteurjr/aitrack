import React from 'react';
import { render, screen } from '@testing-library/react';
import OperationModeBadge from './OperationModeBadge';
import { resolveOperationMode } from '../config/operationMode';
import { runtimeEnvironmentService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  runtimeEnvironmentService: { getCurrent: jest.fn() },
}));

const mockedGetCurrent = runtimeEnvironmentService.getCurrent as jest.Mock;

const environment = (mode: string, generatedAt = new Date().toISOString()) => ({
  data: {
    schema_version: 'runtime-environment.v1', generated_at: generatedAt, mode,
    authority: 'test', safe_for_real_actions: mode === 'production', issues: [],
    sources: [
      { source: 'tracker', label: 'Tracker', mode, configured: true },
      { source: 'dirijabem', label: 'Dirija Bem', mode, configured: true },
    ],
  },
});

describe('resolveOperationMode', () => {
  it.each([
    ['simulation', 'simulation', 'SIMULAÇÃO'],
    ['replay', 'replay', 'REPLAY'],
    ['production', 'production', 'PRODUÇÃO'],
    [' produção ', 'production', 'PRODUÇÃO'],
    ['mixed', 'mixed', 'MISTO'],
    ['unknown', 'unknown', 'NÃO CONFIRMADO'],
  ])('resolve %s como %s', (value, expectedMode, expectedLabel) => {
    const result = resolveOperationMode(value);

    expect(result.mode).toBe(expectedMode);
    expect(result.label).toBe(expectedLabel);
  });

  it.each([undefined, '', 'valor-invalido', 'live'])(
    'usa modo não confirmado como fallback seguro para %s',
    (value) => {
      expect(resolveOperationMode(value).mode).toBe('unknown');
    },
  );
});

describe('OperationModeBadge', () => {
  beforeEach(() => jest.clearAllMocks());

  it.each([
    ['production', 'PRODUÇÃO'],
    ['simulation', 'SIMULAÇÃO'],
    ['replay', 'REPLAY'],
    ['mixed', 'MISTO'],
    ['unknown', 'NÃO CONFIRMADO'],
  ])('expõe %s recebido do backend como status global', async (mode, label) => {
    mockedGetCurrent.mockResolvedValue(environment(mode));
    render(<OperationModeBadge />);

    expect(await screen.findByRole('status', { name: `Ambiente: ${label}` })).toHaveTextContent(
      `AMBIENTE: ${label}`,
    );
  });

  it('nunca mantém produção quando o backend fica indisponível', async () => {
    mockedGetCurrent.mockRejectedValue(new Error('offline'));
    render(<OperationModeBadge />);

    expect(await screen.findByRole('status', { name: 'Ambiente: NÃO CONFIRMADO' }))
      .toHaveAttribute('data-mode', 'unknown');
  });

  it('rejeita snapshot vencido mesmo que declare produção', async () => {
    mockedGetCurrent.mockResolvedValue(environment('production', '2026-01-01T00:00:00Z'));
    render(<OperationModeBadge />);

    expect(await screen.findByRole('status', { name: 'Ambiente: NÃO CONFIRMADO' }))
      .toHaveAttribute('title', expect.stringContaining('desatualizado'));
  });

  it('rejeita timestamp inválido em vez de manter produção', async () => {
    mockedGetCurrent.mockResolvedValue(environment('production', 'não-é-data'));
    render(<OperationModeBadge />);

    expect(await screen.findByRole('status', { name: 'Ambiente: NÃO CONFIRMADO' }))
      .toHaveAttribute('data-mode', 'unknown');
  });
});
