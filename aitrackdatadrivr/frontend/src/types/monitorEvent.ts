export type EventCategory = 'critical' | 'behavioral' | 'operational';
export type EventSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface EventType {
  id: number;
  codigo: string;
  nome: string;
  categoria: EventCategory;
  severidade_padrao: EventSeverity;
  icone: string;
  cor: string;
  descricao: string;
}

export interface MonitorEvent {
  id: number;
  tipo_evento_codigo: string;
  tipo_evento_nome: string;
  categoria: EventCategory;
  severidade: EventSeverity;
  device_id: string;
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  velocidade?: number | null;
  dados_adicionais: Record<string, unknown> | null;
}

export interface EventStats {
  total_eventos_hoje: number;
  por_tipo: Record<string, number>;
  por_categoria: Partial<Record<EventCategory, number>>;
}
