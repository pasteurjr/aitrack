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

const commandKey = (action: string, incidentId: number) => {
  const random = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `ui:${action}:${incidentId}:${random}`;
};

const localOperatorId = () => {
  const stored = window.localStorage.getItem('aitrack.operator.id');
  if (stored) return stored;
  const created = `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem('aitrack.operator.id', created);
  return created;
};

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
  const [operatorId] = useState(localOperatorId);
  const [operatorName, setOperatorName] = useState(
    () => window.localStorage.getItem('aitrack.operator.name') || '',
  );
  const [comment, setComment] = useState('');
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState('');

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

  const runCommand = async (action: 'acknowledge' | 'assume' | 'comment') => {
    if (!selectedIncident || !operatorName.trim()) return;
    setActionBusy(true);
    setActionError('');
    const body = {
      expected_version: selectedIncident.version,
      idempotency_key: commandKey(action, selectedIncident.id),
      operator: { id: operatorId, name: operatorName.trim() },
    };
    try {
      if (action === 'acknowledge') {
        await incidentService.acknowledge(selectedIncident.id, body);
      } else if (action === 'assume') {
        await incidentService.assume(selectedIncident.id, body);
      } else {
        await incidentService.comment(selectedIncident.id, { ...body, comment: comment.trim() });
        setComment('');
      }
      window.localStorage.setItem('aitrack.operator.name', operatorName.trim());
      retry();
    } catch (requestError: any) {
      setActionError(
        requestError?.response?.data?.error
        || 'Não foi possível registrar a ação. Recarregue o incidente e tente novamente.',
      );
    } finally {
      setActionBusy(false);
    }
  };

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
          operatorName={operatorName}
          comment={comment}
          actionBusy={actionBusy}
          actionError={actionError}
          onOperatorNameChange={setOperatorName}
          onCommentChange={setComment}
          onAcknowledge={() => runCommand('acknowledge')}
          onAssume={() => runCommand('assume')}
          onComment={() => runCommand('comment')}
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
  operatorName: string;
  comment: string;
  actionBusy: boolean;
  actionError: string;
  onOperatorNameChange: (value: string) => void;
  onCommentChange: (value: string) => void;
  onAcknowledge: () => void;
  onAssume: () => void;
  onComment: () => void;
}> = ({
  incident, loading, error, onBack, onRetry, onVehicleSelect,
  operatorName, comment, actionBusy, actionError,
  onOperatorNameChange, onCommentChange, onAcknowledge, onAssume, onComment,
}) => (
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
        <section style={{ ...styles.card, cursor: 'default' }}>
          <h3 style={styles.cardTitle}>Ações do operador</h3>
          <label style={styles.actionLabel}>
            Seu nome
            <input
              aria-label="Seu nome"
              value={operatorName}
              maxLength={150}
              onChange={event => onOperatorNameChange(event.target.value)}
              style={styles.actionInput}
              placeholder="Identificação para a auditoria"
            />
          </label>
          <span style={styles.muted}>
            Identidade local para auditoria; ainda não equivale a autenticação de usuário.
          </span>
          <div style={styles.actionRow}>
            {incident.status === 'new' && (
              <button
                type="button"
                disabled={actionBusy || !operatorName.trim()}
                onClick={onAcknowledge}
                style={styles.primaryButton}
              >
                Reconhecer incidente
              </button>
            )}
            {incident.status === 'triage' && (
              <button
                type="button"
                disabled={actionBusy || !operatorName.trim()}
                onClick={onAssume}
                style={styles.primaryButton}
              >
                Assumir atendimento
              </button>
            )}
          </div>
          <label style={{ ...styles.actionLabel, marginTop: '12px' }}>
            Comentário operacional
            <textarea
              aria-label="Comentário operacional"
              value={comment}
              maxLength={2000}
              onChange={event => onCommentChange(event.target.value)}
              style={{ ...styles.actionInput, minHeight: '76px', resize: 'vertical' }}
            />
          </label>
          <button
            type="button"
            disabled={actionBusy || !operatorName.trim() || comment.trim().length < 2}
            onClick={onComment}
            style={styles.secondaryButton}
          >
            Registrar comentário
          </button>
          {actionBusy && <span role="status" style={styles.muted}>Registrando ação…</span>}
          {actionError && <div role="alert" style={styles.actionError}>{actionError}</div>}
        </section>
        <AsyncDataState
          variant="stale"
          compact
          title="Resolução entra na próxima etapa"
          message="Resolver e classificar falso positivo serão comandos reais na UI-2.8."
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
  actionLabel: { color: '#d1d5db', display: 'flex', flexDirection: 'column', fontSize: '12px', gap: '5px' },
  actionInput: { backgroundColor: '#1f2937', border: '1px solid #4b5563', borderRadius: '5px', color: '#f9fafb', padding: '8px' },
  actionRow: { display: 'flex', gap: '8px', marginTop: '12px' },
  primaryButton: { backgroundColor: '#2563eb', border: 0, borderRadius: '6px', color: '#fff', cursor: 'pointer', fontWeight: 700, padding: '9px 12px' },
  actionError: { backgroundColor: '#7f1d1d', borderRadius: '5px', color: '#fecaca', fontSize: '12px', marginTop: '10px', padding: '8px' },
};

export default AlertsPanel;
