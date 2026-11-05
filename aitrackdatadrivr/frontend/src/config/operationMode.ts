export type OperationMode = 'simulation' | 'replay' | 'production';

export interface OperationModePresentation {
  mode: OperationMode;
  label: string;
  description: string;
  color: string;
  backgroundColor: string;
}

const MODE_ALIASES: Record<string, OperationMode> = {
  simulation: 'simulation',
  simulacao: 'simulation',
  simulação: 'simulation',
  replay: 'replay',
  production: 'production',
  producao: 'production',
  produção: 'production',
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
};

/**
 * Resolve o modo operacional configurado no build.
 * O fallback é sempre simulação para impedir que um ambiente sem configuração
 * seja apresentado ao operador como produção.
 */
export function resolveOperationMode(value?: string): OperationModePresentation {
  const normalizedValue = value?.trim().toLocaleLowerCase('pt-BR') ?? '';
  const mode = MODE_ALIASES[normalizedValue] ?? 'simulation';

  return MODE_PRESENTATION[mode];
}
