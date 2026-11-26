import { vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';

import { healthIntegrationService } from '../services/apiService';
import HealthIntegrationsPanel from './HealthIntegrationsPanel';
import { axe } from 'jest-axe';

vi.mock('../services/apiService', () => ({
  healthIntegrationService: { getAll: vi.fn() },
}));

const mockedGetAll = healthIntegrationService.getAll as jest.Mock;

const integrations = {
  tracker_ingestion: { status: 'healthy', message: 'Recebendo posições', latency_ms: 42 },
  dirijabem_ingestion: { status: 'degraded', message: 'Dados com atraso' },
  ai_provider: { status: 'up' },
  message_provider: { status: 'online' },
  voice_provider: { status: 'outage' },
  agent_worker: { status: 'ok' },
  action_worker: { status: 'degraded' },
  report_worker: { status: 'healthy' },
  database: { status: 'healthy' },
};

beforeEach(() => vi.clearAllMocks());

test('exibe loading enquanto consulta a API', () => {
  mockedGetAll.mockReturnValue(new Promise(() => undefined));
  render(<HealthIntegrationsPanel />);

  expect(screen.getByRole('status')).toHaveTextContent('Consultando integrações');
});

test('exibe erro acessível e permite tentar novamente', async () => {
  mockedGetAll.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: { integrations } });
  render(<HealthIntegrationsPanel />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Saúde indisponível');
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

  expect(await screen.findByRole('heading', { name: 'Saúde e integrações' })).toBeInTheDocument();
  expect(mockedGetAll).toHaveBeenCalledTimes(2);
});

test('exibe estado vazio quando a API não retorna componentes', async () => {
  mockedGetAll.mockResolvedValue({ data: { integrations: [] } });
  render(<HealthIntegrationsPanel />);

  expect(await screen.findByText('Nenhuma integração encontrada')).toBeInTheDocument();
});

test('renderiza os sete cartões com nomes, estados e detalhes acessíveis', async () => {
  mockedGetAll.mockResolvedValue({
    data: { generated_at: '2026-11-25T12:00:00Z', overall_status: 'degraded', integrations,
      active_alerts: [{ alert_key: 'health:voice', component_key: 'voice_provider', severity: 'high', summary: 'Voz indisponível' }] },
  });
  render(<HealthIntegrationsPanel />);

  expect(await screen.findByText('Estado geral: Degradado. Alertas técnicos ativos: 1')).toBeInTheDocument();
  const region = screen.getByRole('region', { name: 'Integrações monitoradas' });
  expect(within(region).getAllByRole('article')).toHaveLength(7);
  expect(screen.getByRole('article', { name: 'Tracker: Saudável' })).toHaveTextContent('42 ms');
  expect(screen.getByRole('article', { name: 'Dirija Bem: Degradado' })).toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'IA: Saudável' })).toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Mensagens: Saudável' })).toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Voz: Indisponível' })).toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Workers: Degradado' })).toHaveTextContent('3 processos verificados.');
  expect(screen.getByRole('article', { name: 'Banco de dados: Saudável' })).toBeInTheDocument();
});

test('painel preenchido não possui violação axe detectável', async () => {
  mockedGetAll.mockResolvedValue({ data: { overall_status: 'healthy', integrations } });
  const { container } = render(<HealthIntegrationsPanel />);
  await screen.findByRole('heading', { name: 'Saúde e integrações' });
  expect(await axe(container)).toHaveNoViolations();
});
