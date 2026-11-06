import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { incidentService } from '../services/apiService';
import type {
  IncidentDetail,
  IncidentSeverity,
  IncidentStatus,
  IncidentSummary,
} from '../types/incident';
import AsyncDataState from './AsyncDataState';

interface AlertsPanelProps {
  onVehicleSelect?: (deviceId: string) => void;
}

type StatusFilter = 'open' | 'all' | IncidentStatus;
type SeverityFilter = 'all' | IncidentSeverity;

const STATUS_LABELS: Record<IncidentStatus, string> = {
  new: 'Novo',
  triage: 'Em triagem',
  in_progress: 'Em atendimento',
  waiting_response: 'Aguardando resposta',
  escalated: 'Escalado',
  resolved: 'Resolvido',
  closed: 'Encerrado',
};

const SEVERITY_LABELS: Record<IncidentSeverity, string> = {
  critical: 'Crítica',
  high: 'Alta',
  medium: 'Média',
  low: 'Baixa',
};

const SOURCE_LABELS = {
  tracker: 'Tracker',
  dirijabem: 'Dirija Bem',
  fused: 'Tracker + Dirija Bem',
  system: 'Sistema',
};

const severityColor = (severity: IncidentSeverity) => ({
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#84cc16',
}[severity]);

const statusColor = (status: IncidentStatus) => ({
  new: '#f59e0b',
  triage: '#8b5cf6',
  in_progress: '#3b82f6',
  waiting_response: '#0891b2',
  escalated: '#dc2626',
  resolved: '#10b981',
  closed: '#6b7280',
}[status]);

const formatDateTime = (timestamp: string) => new Date(timestamp).toLocaleString('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const AlertsPanel: React.FC<AlertsPanelProps> = ({ onVehicleSelect }) => {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('open');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<IncidentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  const loadIncidents = useCallback(() => {
    setLoading(true);
    setError(false);
    const filters = {
      limit: 200,
      ...(statusFilter === 'open' ? { open_only: true } : {}),
      ...(statusFilter !== 'open' && statusFilter !== 'all' ? { status: statusFilter } : {}),
      ...(severityFilter !== 'all' ? { severity: severityFilter } : {}),
    };
    let active = true;
    incidentService.getAll(filters).then(({ data }) => {
      if (!active) return;
      setIncidents(data.incidents);
      setTotal(data.total);
      setLoading(false);
    }).catch(() => {
      if (!active) return;
      setError(true);
      setLoading(false);
    });
    return () => { active = false; };
  }, [severityFilter, statusFilter]);

  useEffect(() => loadIncidents(), [loadIncidents, refreshToken]);

  useEffect(() => {
    if (selectedId === null) {
      setSelectedIncident(null);
      return undefined;
    }
    let active = true;
    setDetailLoading(true);
    setDetailError(false);
    incidentService.getById(selectedId).then(({ data }) => {
      if (!active) return;
      setSelectedIncident(data.incident);
      setDetailLoading(false);
    }).catch(() => {
      if (!active) return;
      setDetailError(true);
      setDetailLoading(false);
    });
    return () => { active = false; };
  }, [selectedId, refreshToken]);

  const stats = useMemo(() => ({
    total,
    critical: incidents.filter(item => item.severity === 'critical').length,
    high: incidents.filter(item => item.severity === 'high').length,
    escalated: incidents.filter(item => item.status === 'escalated').length,
  }), [incidents, total]);

  const retry = () => setRefreshToken(value => value + 1);

  return (
    <div style={styles.panel}>
      {selectedId === null ? (
        <>
          <QueueHeader stats={stats} onRefresh={retry} />
          <QueueFilters
            status={statusFilter}
            severity={severityFilter}
            onStatusChange={setStatusFilter}
            onSeverityChange={setSeverityFilter}
          />
          {loading && <AsyncDataState variant="loading" message="Consultando a fila operacional de incidentes." />}
          {!loading && error && (
            <AsyncDataState
              variant="error"
              message="A fila real não pôde ser consultada. Nenhum alerta foi inventado."
              onRetry={retry}
            />
          )}
          {!loading && !error && incidents.length === 0 && (
            <AsyncDataState
              variant="empty"
              title="Fila sem incidentes"
              message="Não há incidentes reais para os filtros selecionados."
            />
          )}
          {!loading && !error && incidents.length > 0 && (
            <IncidentList
              incidents={incidents}
              onIncidentClick={setSelectedId}
              onVehicleSelect={onVehicleSelect}
            />
          )}
        </>
      ) : (
        <IncidentDetails
          incident={selectedIncident}
          loading={detailLoading}
          error={detailError}
          onBack={() => setSelectedId(null)}
          onRetry={retry}
          onVehicleSelect={onVehicleSelect}
        />
      )}
    </div>
  );
};

const QueueHeader: React.FC<{
  stats: { total: number; critical: number; high: number; escalated: number };
  onRefresh: () => void;
}> = ({ stats, onRefresh }) => (
  <div style={styles.header}>
    <div style={styles.titleRow}>
      <div>
        <h2 style={styles.title}>Fila de incidentes</h2>
        <span style={styles.subtitle}>Dados operacionais persistidos e auditáveis</span>
      </div>
      <button type="button" onClick={onRefresh} style={styles.secondaryButton}>Atualizar</button>
    </div>
    <div style={styles.statsGrid}>
      <Stat value={stats.total} label="Na consulta" color="#f9fafb" />
      <Stat value={stats.critical} label="Críticos carregados" color="#ef4444" />
      <Stat value={stats.high} label="Altos carregados" color="#f97316" />
      <Stat value={stats.escalated} label="Escalados carregados" color="#dc2626" />
    </div>
  </div>
);

const Stat: React.FC<{ value: number; label: string; color: string }> = ({ value, label, color }) => (
  <div style={styles.statBox}>
    <div style={{ color, fontSize: '20px', fontWeight: 'bold' }}>{value}</div>
    <div style={{ color: '#9ca3af', fontSize: '11px' }}>{label}</div>
  </div>
);

const QueueFilters: React.FC<{
  status: StatusFilter;
  severity: SeverityFilter;
  onStatusChange: (value: StatusFilter) => void;
  onSeverityChange: (value: SeverityFilter) => void;
}> = ({ status, severity, onStatusChange, onSeverityChange }) => (
  <div style={styles.filters}>
    <label style={styles.filterLabel}>
      Estado
      <select
        aria-label="Estado"
        style={styles.filterSelect}
        value={status}
        onChange={event => onStatusChange(event.target.value as StatusFilter)}
      >
        <option value="open">Somente abertos</option>
        <option value="all">Todos</option>
        {Object.entries(STATUS_LABELS).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
    </label>
    <label style={styles.filterLabel}>
      Severidade
      <select
        aria-label="Severidade"
        style={styles.filterSelect}
        value={severity}
        onChange={event => onSeverityChange(event.target.value as SeverityFilter)}
      >
        <option value="all">Todas</option>
        {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
    </label>
  </div>
);

const IncidentList: React.FC<{
  incidents: IncidentSummary[];
  onIncidentClick: (id: number) => void;
  onVehicleSelect?: (deviceId: string) => void;
}> = ({ incidents, onIncidentClick, onVehicleSelect }) => (
  <div style={styles.content}>
    {incidents.map(incident => (
      <article
        key={incident.id}
        style={{ ...styles.card, borderLeft: `4px solid ${severityColor(incident.severity)}` }}
        onClick={() => onIncidentClick(incident.id)}
      >
        <div style={styles.cardHeader}>
          <div>
            <h3 style={styles.cardTitle}>{incident.title}</h3>
            <span style={styles.muted}>#{incident.id} · {SOURCE_LABELS[incident.primary_source]}</span>
          </div>
          <div style={styles.badges}>
            <Badge label={SEVERITY_LABELS[incident.severity]} color={severityColor(incident.severity)} />
            <Badge label={STATUS_LABELS[incident.status]} color={statusColor(incident.status)} />
          </div>
        </div>
        <p style={styles.description}>{incident.summary || 'Sem resumo adicional.'}</p>
        <div style={styles.cardFooter}>
          <button
            type="button"
            disabled={!incident.device_id || !onVehicleSelect}
            onClick={event => {
              event.stopPropagation();
              if (incident.device_id && onVehicleSelect) onVehicleSelect(incident.device_id);
            }}
            style={styles.vehicleButton}
          >
            {incident.placa || incident.device_id || `Dirija Bem ${incident.codusu}`}
          </button>
          <span>{incident.event_count} evidência(s) · {formatDateTime(incident.opened_at)}</span>
        </div>
      </article>
    ))}
  </div>
);

const Badge: React.FC<{ label: string; color: string }> = ({ label, color }) => (
  <span style={{ ...styles.badge, backgroundColor: color }}>{label}</span>
);

const IncidentDetails: React.FC<{
  incident: IncidentDetail | null;
  loading: boolean;
  error: boolean;
  onBack: () => void;
  onRetry: () => void;
  onVehicleSelect?: (deviceId: string) => void;
}> = ({ incident, loading, error, onBack, onRetry, onVehicleSelect }) => (
  <>
    <div style={styles.header}>
      <button type="button" onClick={onBack} style={styles.secondaryButton}>← Voltar à fila</button>
    </div>
    {loading && <AsyncDataState variant="loading" message="Carregando o incidente e sua timeline." />}
    {!loading && error && (
      <AsyncDataState
        variant="error"
        message="O detalhe real do incidente não pôde ser carregado."
        onBack={onBack}
        onRetry={onRetry}
      />
    )}
    {!loading && !error && incident && (
      <div style={styles.content}>
        <article style={{ ...styles.card, borderLeft: `4px solid ${severityColor(incident.severity)}` }}>
          <div style={styles.badges}>
            <Badge label={SEVERITY_LABELS[incident.severity]} color={severityColor(incident.severity)} />
            <Badge label={STATUS_LABELS[incident.status]} color={statusColor(incident.status)} />
            <Badge label={SOURCE_LABELS[incident.primary_source]} color="#2563eb" />
          </div>
          <h2 style={{ ...styles.cardTitle, fontSize: '18px', marginTop: '12px' }}>{incident.title}</h2>
          <p style={styles.description}>{incident.summary || 'Sem resumo adicional.'}</p>
          <dl style={styles.detailsGrid}>
            <Detail label="Veículo" value={incident.placa || incident.device_id || `Dirija Bem ${incident.codusu}`} />
            <Detail label="Tipo" value={incident.incident_type} />
            <Detail label="Monitor" value={incident.monitor_name || 'Sem monitor associado'} />
            <Detail label="Responsável" value={incident.assigned_to || 'Não atribuído'} />
            <Detail label="Risco" value={incident.risk_score === null ? 'Não calculado' : `${incident.risk_score.toFixed(1)}/100`} />
            <Detail label="Aberto em" value={formatDateTime(incident.opened_at)} />
          </dl>
          {incident.device_id && onVehicleSelect && (
            <button type="button" style={styles.secondaryButton} onClick={() => onVehicleSelect(incident.device_id!)}>
              Abrir veículo no mapa
            </button>
          )}
        </article>
        <section style={{ ...styles.card, cursor: 'default' }}>
          <h3 style={styles.cardTitle}>Timeline auditável ({incident.timeline_total})</h3>
          {incident.timeline.length === 0 ? (
            <p style={styles.muted}>Nenhuma entrada registrada.</p>
          ) : incident.timeline.map(entry => (
            <div key={entry.id} style={styles.timelineEntry}>
              <strong style={{ color: '#f9fafb' }}>{entry.summary}</strong>
              <span style={styles.muted}>
                {entry.actor_name || entry.actor_id || entry.actor_type} · {formatDateTime(entry.occurred_at)}
              </span>
            </div>
          ))}
        </section>
        <AsyncDataState
          variant="stale"
          compact
          title="Ações ainda bloqueadas nesta tela"
          message="Reconhecer, assumir e comentar entram na etapa 2.7; resolver e classificar falso positivo, na 2.8."
        />
      </div>
    )}
  </>
);

const Detail: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <dt style={styles.muted}>{label}</dt>
    <dd style={{ color: '#f9fafb', margin: '3px 0 0' }}>{value}</dd>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  panel: { backgroundColor: '#1f2937', display: 'flex', flexDirection: 'column', height: '100%' },
  header: { backgroundColor: '#111827', borderBottom: '1px solid #374151', padding: '15px 20px' },
  titleRow: { alignItems: 'center', display: 'flex', justifyContent: 'space-between' },
  title: { color: '#f9fafb', fontSize: '18px', margin: 0 },
  subtitle: { color: '#9ca3af', fontSize: '11px' },
  statsGrid: { display: 'grid', gap: '10px', gridTemplateColumns: 'repeat(4, 1fr)', marginTop: '15px' },
  statBox: { backgroundColor: '#374151', borderRadius: '6px', padding: '10px', textAlign: 'center' },
  filters: { backgroundColor: '#111827', borderBottom: '1px solid #374151', display: 'flex', gap: '15px', padding: '12px 20px' },
  filterLabel: { color: '#9ca3af', display: 'flex', flexDirection: 'column', fontSize: '12px', gap: '4px' },
  filterSelect: { backgroundColor: '#374151', border: '1px solid #4b5563', borderRadius: '4px', color: '#f9fafb', padding: '6px 10px' },
  content: { flex: 1, overflowY: 'auto', padding: '15px' },
  card: { backgroundColor: '#374151', borderRadius: '8px', cursor: 'pointer', marginBottom: '12px', padding: '15px' },
  cardHeader: { alignItems: 'flex-start', display: 'flex', gap: '12px', justifyContent: 'space-between' },
  cardTitle: { color: '#f9fafb', fontSize: '14px', margin: '0 0 4px' },
  badges: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  badge: { borderRadius: '4px', color: '#fff', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', textTransform: 'uppercase' },
  muted: { color: '#9ca3af', display: 'block', fontSize: '12px' },
  description: { color: '#d1d5db', fontSize: '13px', lineHeight: 1.5, margin: '10px 0' },
  cardFooter: { alignItems: 'center', borderTop: '1px solid #4b5563', color: '#9ca3af', display: 'flex', fontSize: '11px', justifyContent: 'space-between', paddingTop: '10px' },
  vehicleButton: { background: 'none', border: 0, color: '#dbeafe', cursor: 'pointer', fontWeight: 700, padding: 0, textDecoration: 'underline' },
  secondaryButton: { backgroundColor: '#374151', border: 'none', borderRadius: '6px', color: '#f9fafb', cursor: 'pointer', fontSize: '12px', padding: '8px 12px' },
  detailsGrid: { display: 'grid', gap: '14px', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', margin: '16px 0' },
  timelineEntry: { borderLeft: '2px solid #60a5fa', marginTop: '12px', paddingLeft: '10px' },
};

export default AlertsPanel;
