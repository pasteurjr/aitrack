export interface Monitor {
  id: number;
  nome: string;
  descricao: string;
  tipo_monitor: 'safety' | 'efficiency' | 'compliance' | 'predictive' | 'custom';
  ativo: boolean;
  intervalo_analise: number;
  janela_contexto: number;
  eventos_minimos: number;
  score_threshold: number;
  gera_alertas: boolean;
  veiculos_monitorados: number;
  criado_em: string;
}

export interface VehicleInMonitor {
  monitor_id: number;
  tipo_veiculo: 'tracker' | 'dirijabem';
  device_id: string;
  nome_motorista?: string;
  score_atual: number;
  total_eventos_hoje: number;
  status: 'ok' | 'warning' | 'critical';
}
