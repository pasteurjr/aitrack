// Mock data for AI Monitors demonstration
// Each monitor watches a GROUP of vehicles and sees ALL event types

export interface Monitor {
  id: number;
  nome: string;
  descricao: string;
  tipo_monitor: 'safety' | 'efficiency' | 'compliance' | 'predictive' | 'custom';
  ativo: boolean;
  intervalo_analise: number; // seconds
  janela_contexto: number; // seconds
  eventos_minimos: number;
  score_threshold: number;
  gera_alertas: boolean;
  veiculos_monitorados: number; // count of vehicles in group
  criado_em: string;
}

export interface VehicleInMonitor {
  monitor_id: number;
  tipo_veiculo: 'tracker' | 'dirijabem';
  device_id: string;
  nome_motorista?: string;
  score_atual: number;
  total_eventos_hoje: number;
}

export const mockMonitors: Monitor[] = [
  {
    id: 1,
    nome: 'Monitor de Segurança Frota Principal',
    descricao: 'Monitora comportamentos de risco e eventos críticos em 12 veículos da frota principal. Analisa todos os eventos (críticos, comportamentais e operacionais) para identificar padrões de risco.',
    tipo_monitor: 'safety',
    ativo: true,
    intervalo_analise: 300, // 5 min
    janela_contexto: 1800, // 30 min
    eventos_minimos: 3,
    score_threshold: 70.0,
    gera_alertas: true,
    veiculos_monitorados: 12,
    criado_em: '2026-02-08T08:00:00',
  },
  {
    id: 2,
    nome: 'Monitor de Eficiência Combustível',
    descricao: 'Monitora consumo de combustível e padrões de condução em 8 veículos de entregas. Analisa acelerações bruscas, frenagens e ralenti excessivo para otimizar custos operacionais.',
    tipo_monitor: 'efficiency',
    ativo: true,
    intervalo_analise: 600, // 10 min
    janela_contexto: 3600, // 60 min
    eventos_minimos: 5,
    score_threshold: 75.0,
    gera_alertas: true,
    veiculos_monitorados: 8,
    criado_em: '2026-02-08T08:15:00',
  },
  {
    id: 3,
    nome: 'Monitor de Fadiga - Motoristas Rodoviários',
    descricao: 'Detecta sinais de fadiga em 5 motoristas de longa distância através da análise temporal de eventos. Monitora aumento de micro-correções, eventos de baixa severidade e padrões de direção errática.',
    tipo_monitor: 'safety',
    ativo: true,
    intervalo_analise: 900, // 15 min
    janela_contexto: 5400, // 90 min
    eventos_minimos: 4,
    score_threshold: 80.0,
    gera_alertas: true,
    veiculos_monitorados: 5,
    criado_em: '2026-02-09T07:30:00',
  },
  {
    id: 4,
    nome: 'Monitor de Conformidade - Velocidade Máxima',
    descricao: 'Monitora violações de limite de velocidade em 15 veículos da frota corporativa. Garante conformidade com políticas internas de segurança viária.',
    tipo_monitor: 'compliance',
    ativo: true,
    intervalo_analise: 300, // 5 min
    janela_contexto: 1800, // 30 min
    eventos_minimos: 2,
    score_threshold: 65.0,
    gera_alertas: true,
    veiculos_monitorados: 15,
    criado_em: '2026-02-09T09:00:00',
  },
  {
    id: 5,
    nome: 'Monitor Preditivo - Manutenção',
    descricao: 'Prevê necessidades de manutenção através de análise de padrões de condução agressiva, ralenti excessivo e eventos mecânicos em 10 veículos.',
    tipo_monitor: 'predictive',
    ativo: false, // Inativo para demonstração
    intervalo_analise: 1800, // 30 min
    janela_contexto: 7200, // 2 hours
    eventos_minimos: 6,
    score_threshold: 70.0,
    gera_alertas: false,
    veiculos_monitorados: 10,
    criado_em: '2026-02-10T06:00:00',
  },
];

export const mockVehiclesInMonitors: VehicleInMonitor[] = [
  // Monitor 1 - Segurança (12 veículos)
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1000', score_atual: 62.3, total_eventos_hoje: 18 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1001', score_atual: 58.7, total_eventos_hoje: 24 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1002', score_atual: 71.2, total_eventos_hoje: 12 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1003', score_atual: 54.8, total_eventos_hoje: 31 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1004', score_atual: 68.9, total_eventos_hoje: 15 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1005', score_atual: 73.4, total_eventos_hoje: 9 },
  { monitor_id: 1, tipo_veiculo: 'dirijabem', device_id: 'USR-2001', nome_motorista: 'João Silva', score_atual: 48.2, total_eventos_hoje: 42 },
  { monitor_id: 1, tipo_veiculo: 'dirijabem', device_id: 'USR-2002', nome_motorista: 'Maria Santos', score_atual: 76.5, total_eventos_hoje: 8 },
  { monitor_id: 1, tipo_veiculo: 'dirijabem', device_id: 'USR-2003', nome_motorista: 'Pedro Costa', score_atual: 65.1, total_eventos_hoje: 19 },
  { monitor_id: 1, tipo_veiculo: 'dirijabem', device_id: 'USR-2004', nome_motorista: 'Ana Paula', score_atual: 59.8, total_eventos_hoje: 27 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1006', score_atual: 81.3, total_eventos_hoje: 5 },
  { monitor_id: 1, tipo_veiculo: 'tracker', device_id: 'SIM-1007', score_atual: 52.6, total_eventos_hoje: 35 },

  // Monitor 2 - Eficiência (8 veículos)
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2000', score_atual: 64.2, total_eventos_hoje: 22 },
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2001', score_atual: 71.8, total_eventos_hoje: 14 },
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2002', score_atual: 58.9, total_eventos_hoje: 28 },
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2003', score_atual: 76.3, total_eventos_hoje: 11 },
  { monitor_id: 2, tipo_veiculo: 'dirijabem', device_id: 'USR-3001', nome_motorista: 'Carlos Mendes', score_atual: 52.4, total_eventos_hoje: 38 },
  { monitor_id: 2, tipo_veiculo: 'dirijabem', device_id: 'USR-3002', nome_motorista: 'Luciana Rocha', score_atual: 69.7, total_eventos_hoje: 17 },
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2004', score_atual: 73.1, total_eventos_hoje: 13 },
  { monitor_id: 2, tipo_veiculo: 'tracker', device_id: 'SIM-2005', score_atual: 61.5, total_eventos_hoje: 25 },

  // Monitor 3 - Fadiga (5 veículos)
  { monitor_id: 3, tipo_veiculo: 'dirijabem', device_id: 'USR-4001', nome_motorista: 'Roberto Lima', score_atual: 78.2, total_eventos_hoje: 9 },
  { monitor_id: 3, tipo_veiculo: 'dirijabem', device_id: 'USR-4002', nome_motorista: 'Fernanda Alves', score_atual: 82.6, total_eventos_hoje: 6 },
  { monitor_id: 3, tipo_veiculo: 'dirijabem', device_id: 'USR-4003', nome_motorista: 'Marcos Pereira', score_atual: 75.9, total_eventos_hoje: 11 },
  { monitor_id: 3, tipo_veiculo: 'dirijabem', device_id: 'USR-4004', nome_motorista: 'Juliana Campos', score_atual: 68.3, total_eventos_hoje: 16 },
  { monitor_id: 3, tipo_veiculo: 'dirijabem', device_id: 'USR-4005', nome_motorista: 'Gustavo Nunes', score_atual: 71.7, total_eventos_hoje: 14 },

  // Monitor 4 - Conformidade (15 veículos)
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3000', score_atual: 63.8, total_eventos_hoje: 21 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3001', score_atual: 58.2, total_eventos_hoje: 29 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3002', score_atual: 72.4, total_eventos_hoje: 12 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3003', score_atual: 67.9, total_eventos_hoje: 18 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3004', score_atual: 55.1, total_eventos_hoje: 34 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3005', score_atual: 74.6, total_eventos_hoje: 10 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3006', score_atual: 61.3, total_eventos_hoje: 24 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3007', score_atual: 69.8, total_eventos_hoje: 15 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3008', score_atual: 76.2, total_eventos_hoje: 9 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3009', score_atual: 52.9, total_eventos_hoje: 37 },
  { monitor_id: 4, tipo_veiculo: 'dirijabem', device_id: 'USR-5001', nome_motorista: 'Renata Souza', score_atual: 79.4, total_eventos_hoje: 7 },
  { monitor_id: 4, tipo_veiculo: 'dirijabem', device_id: 'USR-5002', nome_motorista: 'Thiago Martins', score_atual: 64.7, total_eventos_hoje: 20 },
  { monitor_id: 4, tipo_veiculo: 'dirijabem', device_id: 'USR-5003', nome_motorista: 'Camila Ferreira', score_atual: 71.5, total_eventos_hoje: 13 },
  { monitor_id: 4, tipo_veiculo: 'dirijabem', device_id: 'USR-5004', nome_motorista: 'Felipe Oliveira', score_atual: 57.8, total_eventos_hoje: 30 },
  { monitor_id: 4, tipo_veiculo: 'tracker', device_id: 'SIM-3010', score_atual: 68.1, total_eventos_hoje: 17 },
];
