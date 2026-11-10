import type { RuntimeMode } from '../types/runtimeEnvironment';

export type OperationMode = RuntimeMode | 'checking';

export interface OperationModePresentation {
  mode: OperationMode;
  label: string;
  description: string;
  color: string;
  backgroundColor: string;
}

const MODE_ALIASES: Record<string, RuntimeMode> = {
  simulation: 'simulation',
  simulacao: 'simulation',
  simulação: 'simulation',
  replay: 'replay',
  production: 'production',
  producao: 'production',
  produção: 'production',
  mixed: 'mixed',
  misto: 'mixed',
  unknown: 'unknown',
};

const MODE_PRESENTATION: Record<OperationMode, OperationModePresentation> = {
  simulation: {
    mode: 'simulation',
    label: 'SIMULAÇÃO',
    description: 'Dados podem ser gerados por simuladores e não representam uma operação real.',
    color: '#fef3c7',
    backgroundColor: '#92400e',
  },
  replay: {
    mode: 'replay',
    label: 'REPLAY',
    description: 'Dados históricos estão sendo reproduzidos para análise ou teste.',
    color: '#dbeafe',
    backgroundColor: '#1e40af',
  },
  production: {
    mode: 'production',
    label: 'PRODUÇÃO',
    description: 'Ambiente operacional com dados e ações reais.',
    color: '#fee2e2',
    backgroundColor: '#991b1b',
  },
  mixed: {
    mode: 'mixed',
    label: 'MISTO',
    description: 'As fontes estão em modos diferentes. Ações reais não são seguras.',
    color: '#fef3c7',
    backgroundColor: '#7c2d12',
  },
  unknown: {
    mode: 'unknown',
    label: 'NÃO CONFIRMADO',
    description: 'O backend não confirmou o ambiente operacional.',
    color: '#f8fafc',
    backgroundColor: '#475569',
  },
  checking: {
    mode: 'checking',
    label: 'VERIFICANDO',
    description: 'Consultando o ambiente operacional no backend.',
    color: '#e2e8f0',
    backgroundColor: '#334155',
  },
};

/**
 * Resolve somente valores recebidos do backend. Valores ausentes ou inválidos
 * são indeterminados; o frontend nunca presume simulação nem produção.
 */
export function resolveOperationMode(value?: string): OperationModePresentation {
  const normalizedValue = value?.trim().toLocaleLowerCase('pt-BR') ?? '';
  const mode = MODE_ALIASES[normalizedValue] ?? 'unknown';

  return MODE_PRESENTATION[mode];
}

export function checkingOperationMode(): OperationModePresentation {
  return MODE_PRESENTATION.checking;
}
