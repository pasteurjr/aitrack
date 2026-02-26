import React, { useState } from 'react';
import { mockAlerts, mockAlertStats } from '../mockData/mockAlerts';
import type { Alert } from '../mockData/mockAlerts';

interface AlertsPanelProps {
  onVehicleSelect?: (deviceId: string) => void;
}

const AlertsPanel: React.FC<AlertsPanelProps> = ({ onVehicleSelect }) => {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const filteredAlerts = mockAlerts.filter(alert => {
    if (filterStatus !== 'all' && alert.status !== filterStatus) return false;
    if (filterSeverity !== 'all' && alert.severidade !== filterSeverity) return false;
    return true;
  });

  const handleAlertClick = (alert: Alert) => {
    setSelectedAlert(alert);
  };

  const handleBack = () => {
    setSelectedAlert(null);
  };

  const handleAcknowledge = (alertId: number) => {
    console.log('Acknowledging alert:', alertId);
    // In real app: API call to acknowledge alert
    alert('Alerta reconhecido! (Mock - não persiste)');
  };

  const handleResolve = (alertId: number) => {
    console.log('Resolving alert:', alertId);
    // In real app: API call to resolve alert
    alert('Alerta resolvido! (Mock - não persiste)');
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1f2937' }}>
      {!selectedAlert ? (
        <>
          <AlertsHeader stats={mockAlertStats} />
          <AlertsFilters
            filterStatus={filterStatus}
            filterSeverity={filterSeverity}
            onStatusChange={setFilterStatus}
            onSeverityChange={setFilterSeverity}
          />
          <AlertsList
            alerts={filteredAlerts}
            onAlertClick={handleAlertClick}
            onVehicleSelect={onVehicleSelect}
          />
        </>
      ) : (
        <AlertDetails
          alert={selectedAlert}
          onBack={handleBack}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
          onVehicleSelect={onVehicleSelect}
        />
      )}
    </div>
  );
};

// Header with statistics
const AlertsHeader: React.FC<{ stats: typeof mockAlertStats }> = ({ stats }) => {
  return (
    <div style={styles.header}>
      <h2 style={styles.title}>🔔 Alertas AI</h2>
      <div style={styles.statsGrid}>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f9fafb' }}>
            {stats.total_alertas_ativos}
          </div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Ativos</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#dc2626' }}>{stats.criticos}</div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Críticos</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#ea580c' }}>{stats.altos}</div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Altos</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#10b981' }}>
            {Math.round(stats.taxa_resolucao_24h * 100)}%
          </div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Taxa Resolução</div>
        </div>
      </div>
    </div>
  );
};

// Filters
const AlertsFilters: React.FC<{
  filterStatus: string;
  filterSeverity: string;
  onStatusChange: (status: string) => void;
  onSeverityChange: (severity: string) => void;
}> = ({ filterStatus, filterSeverity, onStatusChange, onSeverityChange }) => {
  return (
    <div style={styles.filters}>
      <div style={styles.filterGroup}>
        <label style={styles.filterLabel}>Status:</label>
        <select
          style={styles.filterSelect}
          value={filterStatus}
          onChange={e => onStatusChange(e.target.value)}
        >
          <option value="all">Todos</option>
          <option value="pending">Pendente</option>
          <option value="acknowledged">Reconhecido</option>
          <option value="resolved">Resolvido</option>
          <option value="dismissed">Descartado</option>
        </select>
      </div>
      <div style={styles.filterGroup}>
        <label style={styles.filterLabel}>Severidade:</label>
        <select
          style={styles.filterSelect}
          value={filterSeverity}
          onChange={e => onSeverityChange(e.target.value)}
        >
          <option value="all">Todas</option>
          <option value="critical">Crítica</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
      </div>
    </div>
  );
};

// Alerts List
const AlertsList: React.FC<{
  alerts: Alert[];
  onAlertClick: (alert: Alert) => void;
  onVehicleSelect?: (deviceId: string) => void;
}> = ({ alerts, onAlertClick, onVehicleSelect }) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#dc2626';
      case 'high':
        return '#ea580c';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return '#84cc16';
      default:
        return '#6b7280';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#f59e0b';
      case 'acknowledged':
        return '#3b82f6';
      case 'resolved':
        return '#10b981';
      case 'dismissed':
        return '#6b7280';
      default:
        return '#6b7280';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins} min atrás`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h atrás`;
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Pendente',
      acknowledged: 'Reconhecido',
      resolved: 'Resolvido',
      dismissed: 'Descartado',
    };
    return labels[status] || status;
  };

  return (
    <div style={styles.content}>
      {alerts.length === 0 && (
        <div style={{ textAlign: 'center', color: '#9ca3af', padding: '40px 20px' }}>
          Nenhum alerta encontrado com os filtros selecionados
        </div>
      )}
      {alerts.map(alert => (
        <div
          key={alert.id}
          style={{
            ...styles.alertCard,
            borderLeft: `4px solid ${getSeverityColor(alert.severidade)}`,
            cursor: 'pointer',
          }}
          onClick={() => onAlertClick(alert)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: '0 0 4px 0', color: '#f9fafb', fontSize: '14px', fontWeight: 'bold' }}>
                {alert.titulo}
              </h3>
              <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '4px' }}>
                {alert.monitor_nome}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
              <span
                style={{
                  fontSize: '10px',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  backgroundColor: getSeverityColor(alert.severidade),
                  color: 'white',
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                }}
              >
                {alert.severidade}
              </span>
              <span
                style={{
                  fontSize: '10px',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  backgroundColor: getStatusColor(alert.status),
                  color: 'white',
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                }}
              >
                {getStatusLabel(alert.status)}
              </span>
            </div>
          </div>

          <p style={{ margin: '8px 0', color: '#d1d5db', fontSize: '13px', lineHeight: '1.4' }}>
            {alert.mensagem.substring(0, 150)}...
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #4b5563' }}>
            <div style={{ fontSize: '12px', color: '#d1d5db' }}>
              <span
                style={{ fontWeight: 'bold', cursor: onVehicleSelect ? 'pointer' : 'default', textDecoration: onVehicleSelect ? 'underline' : 'none' }}
                onClick={(e) => {
                  if (onVehicleSelect) {
                    e.stopPropagation();
                    onVehicleSelect(alert.device_id);
                  }
                }}
              >
                {alert.device_id}
              </span>
              {alert.nome_motorista && <span> - {alert.nome_motorista}</span>}
            </div>
            <div style={{ fontSize: '11px', color: '#9ca3af' }}>
              {formatTimestamp(alert.criado_em)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Alert Details
const AlertDetails: React.FC<{
  alert: Alert;
  onBack: () => void;
  onAcknowledge: (alertId: number) => void;
  onResolve: (alertId: number) => void;
  onVehicleSelect?: (deviceId: string) => void;
}> = ({ alert, onBack, onAcknowledge, onResolve, onVehicleSelect }) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#dc2626';
      case 'high':
        return '#ea580c';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return '#84cc16';
      default:
        return '#6b7280';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>
          ← Voltar
        </button>
        <h2 style={{ ...styles.title, fontSize: '16px' }}>Detalhes do Alerta</h2>
      </div>

      <div style={styles.content}>
        <div style={{ ...styles.alertCard, borderLeft: `4px solid ${getSeverityColor(alert.severidade)}` }}>
          {/* Header */}
          <div style={{ marginBottom: '15px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{
                  fontSize: '11px',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  backgroundColor: getSeverityColor(alert.severidade),
                  color: 'white',
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                }}
              >
                {alert.severidade}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  textTransform: 'uppercase',
                  fontWeight: 'bold',
                }}
              >
                {alert.tipo}
              </span>
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f9fafb', fontSize: '18px', fontWeight: 'bold' }}>
              {alert.titulo}
            </h3>
            <div style={{ fontSize: '13px', color: '#9ca3af' }}>
              Monitor: <span style={{ color: '#d1d5db' }}>{alert.monitor_nome}</span>
            </div>
          </div>

          {/* Vehicle Info */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '6px' }}>Veículo:</div>
            <div style={{ fontSize: '15px', color: '#f9fafb', fontWeight: 'bold' }}>
              <span
                style={{ cursor: onVehicleSelect ? 'pointer' : 'default', textDecoration: onVehicleSelect ? 'underline' : 'none' }}
                onClick={() => onVehicleSelect && onVehicleSelect(alert.device_id)}
              >
                {alert.device_id}
              </span>
              {alert.nome_motorista && <span style={{ color: '#d1d5db', fontWeight: 'normal' }}> - {alert.nome_motorista}</span>}
            </div>
            <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
              {alert.eventos_relacionados} eventos relacionados
            </div>
          </div>

          {/* Message */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>Descrição:</div>
            <p style={{ margin: 0, color: '#d1d5db', fontSize: '14px', lineHeight: '1.6' }}>
              {alert.mensagem}
            </p>
          </div>

          {/* LLM Analysis */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>🤖 Análise da IA:</div>
            <p style={{ margin: 0, color: '#d1d5db', fontSize: '13px', lineHeight: '1.6' }}>
              {alert.llm_analise_resumo}
            </p>
          </div>

          {/* Recommendations */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '10px' }}>💡 Recomendações:</div>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#d1d5db', fontSize: '13px', lineHeight: '1.6' }}>
              {alert.recomendacoes.map((rec, idx) => (
                <li key={idx} style={{ marginBottom: '6px' }}>{rec}</li>
              ))}
            </ul>
          </div>

          {/* Timestamp */}
          <div style={{ fontSize: '12px', color: '#9ca3af', paddingTop: '10px', borderTop: '1px solid #4b5563' }}>
            Criado em: {formatTimestamp(alert.criado_em)}
            {alert.reconhecido_em && (
              <div style={{ marginTop: '4px' }}>
                Reconhecido em: {formatTimestamp(alert.reconhecido_em)} por {alert.reconhecido_por}
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
            {alert.status === 'pending' && (
              <button
                style={styles.actionButton}
                onClick={() => onAcknowledge(alert.id)}
              >
                ✓ Reconhecer
              </button>
            )}
            {(alert.status === 'pending' || alert.status === 'acknowledged') && (
              <button
                style={{ ...styles.actionButton, backgroundColor: '#10b981' }}
                onClick={() => onResolve(alert.id)}
              >
                ✓ Resolver
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  header: {
    padding: '15px 20px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #374151',
  },
  title: {
    margin: 0,
    color: '#f9fafb',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
    marginTop: '15px',
  },
  statBox: {
    backgroundColor: '#374151',
    padding: '10px',
    borderRadius: '6px',
    textAlign: 'center',
  },
  filters: {
    padding: '15px 20px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #374151',
    display: 'flex',
    gap: '15px',
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  filterLabel: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  filterSelect: {
    padding: '6px 10px',
    backgroundColor: '#374151',
    color: '#f9fafb',
    border: '1px solid #4b5563',
    borderRadius: '4px',
    fontSize: '13px',
    cursor: 'pointer',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '15px',
  },
  alertCard: {
    backgroundColor: '#374151',
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '12px',
  },
  backButton: {
    padding: '8px 12px',
    backgroundColor: '#374151',
    color: '#f9fafb',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    marginBottom: '10px',
  },
  infoBox: {
    backgroundColor: '#1f2937',
    padding: '12px',
    borderRadius: '6px',
  },
  actionButton: {
    padding: '10px 20px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    transition: 'all 0.2s ease',
  },
};

export default AlertsPanel;
