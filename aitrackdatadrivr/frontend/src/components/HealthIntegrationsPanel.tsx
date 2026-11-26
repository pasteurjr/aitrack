import React, { useCallback, useEffect, useState } from 'react';

import { healthIntegrationService } from '../services/apiService';
import type {
  IntegrationHealthCollection,
  IntegrationHealthItem,
  IntegrationHealthResponse,
  IntegrationHealthStatus,
} from '../types/health';
import AsyncDataState from './AsyncDataState';
import './HealthIntegrationsPanel.css';

interface HealthCardDefinition {
  aliases: string[];
  key: string;
  label: string;
}

interface HealthCardData extends HealthCardDefinition {
  checkedAt?: string;
  latencyMs?: number;
  message: string;
  status: IntegrationHealthStatus;
}

const CARD_DEFINITIONS: HealthCardDefinition[] = [
  { key: 'tracker', label: 'Tracker', aliases: ['tracker', 'tracker_ingestion', 'aitrack'] },
  { key: 'dirijabem', label: 'Dirija Bem', aliases: ['dirijabem', 'dirijabem_ingestion', 'dirija_bem', 'data_driver', 'datadrivr'] },
  { key: 'ai', label: 'IA', aliases: ['ai', 'ia', 'ai_provider', 'llm', 'claude', 'artificial_intelligence'] },
  { key: 'messages', label: 'Mensagens', aliases: ['messages', 'message', 'message_provider', 'messaging', 'whatsapp', 'sms'] },
  { key: 'voice', label: 'Voz', aliases: ['voice', 'voice_provider', 'calls', 'telephony', 'telefonia'] },
  { key: 'workers', label: 'Workers', aliases: ['workers', 'worker', 'agent_worker', 'action_worker', 'report_worker', 'jobs', 'queues'] },
  { key: 'database', label: 'Banco de dados', aliases: ['database', 'db', 'mysql', 'banco'] },
];

const STATUS_PRESENTATION: Record<IntegrationHealthStatus, { color: string; label: string }> = {
  healthy: { color: '#34d399', label: 'Saudável' },
  degraded: { color: '#fbbf24', label: 'Degradado' },
  unhealthy: { color: '#f87171', label: 'Indisponível' },
  unknown: { color: '#94a3b8', label: 'Desconhecido' },
};

const normalizeKey = (value: string) => value.trim().toLowerCase().replace(/[\s-]+/g, '_');

const normalizeStatus = (value?: string): IntegrationHealthStatus => {
  const status = normalizeKey(value ?? '');
  if (['healthy', 'ok', 'online', 'up', 'available', 'operational'].includes(status)) return 'healthy';
  if (['degraded', 'warning', 'warn', 'stale', 'partial'].includes(status)) return 'degraded';
  if (['unhealthy', 'error', 'offline', 'down', 'outage', 'unavailable', 'failed'].includes(status)) return 'unhealthy';
  return 'unknown';
};

const toEntries = (collection?: IntegrationHealthCollection): Array<[string, IntegrationHealthItem]> => {
  if (!collection) return [];
  if (Array.isArray(collection)) {
    return collection.map((item, index) => [item.component_key ?? item.key ?? item.id ?? item.name ?? item.label ?? String(index), item]);
  }
  return Object.entries(collection).map(([key, value]) => [
    key,
    typeof value === 'string' ? { status: value } : value,
  ]);
};

const readCollection = (payload: IntegrationHealthResponse): IntegrationHealthCollection | undefined =>
  payload.integrations
  ?? payload.components
  ?? payload.data?.integrations
  ?? payload.data?.components;

export const buildHealthCards = (payload: IntegrationHealthResponse): HealthCardData[] => {
  const entries = toEntries(readCollection(payload));
  if (entries.length === 0) return [];

  return CARD_DEFINITIONS.map(definition => {
    const matches = entries.filter(([entryKey, item]) => {
      const candidates = [entryKey, item.component_key, item.key, item.id, item.name, item.label, item.display_name]
        .filter((value): value is string => Boolean(value))
        .map(normalizeKey);
      return definition.aliases.some(alias => candidates.includes(alias));
    });
    const severity: Record<IntegrationHealthStatus, number> = { healthy: 0, unknown: 1, degraded: 2, unhealthy: 3 };
    const items = matches.map(([, item]) => item);
    const item = items.reduce<IntegrationHealthItem | undefined>((worst, current) => (
      !worst || severity[normalizeStatus(current.status)] > severity[normalizeStatus(worst.status)] ? current : worst
    ), undefined);
    const latencyValues = items.map(value => value.latency_ms).filter((value): value is number => typeof value === 'number');
    return {
      ...definition,
      checkedAt: item?.checked_at ?? item?.heartbeat_at ?? item?.last_success_at,
      latencyMs: latencyValues.length ? Math.max(...latencyValues) : undefined,
      message: item?.message ?? item?.detail ?? item?.reason_sanitized
        ?? (items.length > 1 ? `${items.length} processos verificados.` : item ? 'Integração verificada.' : 'Sem dados desta integração.'),
      status: normalizeStatus(item?.status),
    };
  });
};

const formatTimestamp = (value?: string) => {
  if (!value) return 'Não informado';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Não informado' : date.toLocaleString('pt-BR');
};

const HealthIntegrationsPanel: React.FC = () => {
  const [payload, setPayload] = useState<IntegrationHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await healthIntegrationService.getAll();
      setPayload(response.data);
    } catch {
      setPayload(null);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const refresh = window.setInterval(() => { void load(); }, 30_000);
    return () => window.clearInterval(refresh);
  }, [load]);

  if (loading) return <AsyncDataState variant="loading" title="Consultando integrações" message="Verificando os componentes operacionais." />;
  if (error) return <AsyncDataState variant="error" title="Saúde indisponível" message="Não foi possível consultar as integrações." onRetry={load} />;

  const cards = buildHealthCards(payload ?? {});
  if (cards.length === 0) {
    return <AsyncDataState variant="empty" title="Nenhuma integração encontrada" message="A API respondeu sem componentes de saúde." onRetry={load} />;
  }

  const overall = normalizeStatus(payload?.overall_status ?? payload?.status);
  const overallPresentation = STATUS_PRESENTATION[overall];

  return (
    <section className="health-panel" aria-labelledby="health-panel-title">
      <header className="health-panel__header">
        <div>
          <h2 id="health-panel-title">Saúde e integrações</h2>
          <p>Estado operacional dos serviços usados pelo monitoramento veicular.</p>
        </div>
        <span className="health-panel__summary" role="status">
          Estado geral: {overallPresentation.label}. Alertas técnicos ativos: {payload?.active_alerts?.length ?? 0}
        </span>
      </header>
      <section className="health-panel__grid" aria-label="Integrações monitoradas">
        {cards.map(card => {
          const presentation = STATUS_PRESENTATION[card.status];
          return (
            <article
              className="health-card"
              key={card.key}
              aria-label={`${card.label}: ${presentation.label}`}
              style={{ '--health-color': presentation.color } as React.CSSProperties}
            >
              <div className="health-card__title-row">
                <h3>{card.label}</h3>
                <span className="health-card__status">{presentation.label}</span>
              </div>
              <p className="health-card__message">{card.message}</p>
              <dl>
                <dt>Última verificação</dt>
                <dd>{formatTimestamp(card.checkedAt ?? payload?.generated_at ?? payload?.checked_at)}</dd>
                {typeof card.latencyMs === 'number' && <>
                  <dt>Latência</dt>
                  <dd>{card.latencyMs} ms</dd>
                </>}
              </dl>
            </article>
          );
        })}
      </section>
    </section>
  );
};

export default HealthIntegrationsPanel;
