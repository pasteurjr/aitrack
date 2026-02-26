import React, { useState } from 'react';
import { mockMonitors, mockVehiclesInMonitors } from '../mockData/mockMonitors';
import { mockEvents, eventTypesCatalog } from '../mockData/mockEvents';
import type { Monitor, VehicleInMonitor } from '../mockData/mockMonitors';
import type { Event } from '../mockData/mockEvents';

interface MonitorDashboardProps {
  onVehicleSelect?: (deviceId: string) => void;
}

const MonitorDashboard: React.FC<MonitorDashboardProps> = ({ onVehicleSelect }) => {
  const [selectedMonitor, setSelectedMonitor] = useState<Monitor | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'details'>('list');

  const handleMonitorClick = (monitor: Monitor) => {
    setSelectedMonitor(monitor);
    setViewMode('details');
  };

  const handleBack = () => {
    setViewMode('list');
    setSelectedMonitor(null);
  };

  // Get vehicles for selected monitor
  const getMonitorVehicles = (monitorId: number): VehicleInMonitor[] => {
    return mockVehiclesInMonitors.filter(v => v.monitor_id === monitorId);
  };

  // Get all events from vehicles in monitor
  const getMonitorEvents = (monitorId: number): Event[] => {
    const vehicles = getMonitorVehicles(monitorId);
    const deviceIds = vehicles.map(v => v.device_id);
    return mockEvents.filter(e => deviceIds.includes(e.device_id));
  };

  // Group events by category
  const groupEventsByCategory = (events: Event[]) => {
    return {
      critical: events.filter(e => e.categoria === 'critical'),
      behavioral: events.filter(e => e.categoria === 'behavioral'),
      operational: events.filter(e => e.categoria === 'operational'),
    };
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1f2937' }}>
      {viewMode === 'list' ? (
        <MonitorList monitors={mockMonitors} onMonitorClick={handleMonitorClick} />
      ) : (
        selectedMonitor && (
          <MonitorDetails
            monitor={selectedMonitor}
            vehicles={getMonitorVehicles(selectedMonitor.id)}
            events={getMonitorEvents(selectedMonitor.id)}
            groupedEvents={groupEventsByCategory(getMonitorEvents(selectedMonitor.id))}
            onBack={handleBack}
            onVehicleSelect={onVehicleSelect}
          />
        )
      )}
    </div>
  );
};

// Monitor List View
const MonitorList: React.FC<{ monitors: Monitor[]; onMonitorClick: (m: Monitor) => void }> = ({
  monitors,
  onMonitorClick,
}) => {
  const tipoColors: Record<string, string> = {
    safety: '#ef4444',
    efficiency: '#10b981',
    compliance: '#3b82f6',
    predictive: '#8b5cf6',
    custom: '#6b7280',
  };

  const tipoIcons: Record<string, string> = {
    safety: '🛡️',
    efficiency: '⚡',
    compliance: '✅',
    predictive: '🔮',
    custom: '⚙️',
  };

  return (
    <>
      <div style={styles.header}>
        <h2 style={styles.title}>🤖 Monitores AI</h2>
        <div style={styles.stats}>
          <span style={{ color: '#10b981' }}>{monitors.filter(m => m.ativo).length} Ativos</span>
          <span style={{ color: '#6b7280', marginLeft: '15px' }}>
            {monitors.filter(m => !m.ativo).length} Inativos
          </span>
        </div>
      </div>

      <div style={styles.content}>
        {monitors.map(monitor => (
          <div
            key={monitor.id}
            style={{
              ...styles.monitorCard,
              borderLeft: `4px solid ${tipoColors[monitor.tipo_monitor]}`,
              opacity: monitor.ativo ? 1 : 0.5,
              cursor: 'pointer',
            }}
            onClick={() => onMonitorClick(monitor)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <span style={{ fontSize: '24px' }}>{tipoIcons[monitor.tipo_monitor]}</span>
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, color: '#f9fafb', fontSize: '16px' }}>{monitor.nome}</h3>
                <span
                  style={{
                    fontSize: '11px',
                    color: tipoColors[monitor.tipo_monitor],
                    textTransform: 'uppercase',
                    fontWeight: 'bold',
                  }}
                >
                  {monitor.tipo_monitor}
                </span>
              </div>
              {monitor.ativo && (
                <span style={{ ...styles.badge, backgroundColor: '#10b981' }}>ATIVO</span>
              )}
              {!monitor.ativo && (
                <span style={{ ...styles.badge, backgroundColor: '#6b7280' }}>INATIVO</span>
              )}
            </div>

            <p style={{ margin: '10px 0', color: '#d1d5db', fontSize: '13px', lineHeight: '1.5' }}>
              {monitor.descricao}
            </p>

            <div style={styles.monitorStats}>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Veículos:</span>
                <span style={{ color: '#f9fafb', fontWeight: 'bold' }}>{monitor.veiculos_monitorados}</span>
              </div>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Intervalo:</span>
                <span style={{ color: '#f9fafb' }}>{monitor.intervalo_analise / 60} min</span>
              </div>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Score &lt;:</span>
                <span style={{ color: '#f9fafb' }}>{monitor.score_threshold}</span>
              </div>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Alertas:</span>
                <span style={{ color: monitor.gera_alertas ? '#10b981' : '#6b7280' }}>
                  {monitor.gera_alertas ? 'SIM' : 'NÃO'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
};

// Monitor Details View
const MonitorDetails: React.FC<{
  monitor: Monitor;
  vehicles: VehicleInMonitor[];
  events: Event[];
  groupedEvents: { critical: Event[]; behavioral: Event[]; operational: Event[] };
  onBack: () => void;
  onVehicleSelect?: (deviceId: string) => void;
}> = ({ monitor, vehicles, events, groupedEvents, onBack, onVehicleSelect }) => {
  const [activeTab, setActiveTab] = useState<'vehicles' | 'events'>('vehicles');

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  };

  const getCategoryInfo = (category: string) => {
    switch (category) {
      case 'critical':
        return { icon: '🚨', color: '#dc2626', label: 'Críticos' };
      case 'behavioral':
        return { icon: '⚠️', color: '#f59e0b', label: 'Comportamentais' };
      case 'operational':
        return { icon: '📊', color: '#84cc16', label: 'Operacionais' };
      default:
        return { icon: '•', color: '#6b7280', label: 'Outros' };
    }
  };

  return (
    <>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>
          ← Voltar
        </button>
        <div style={{ flex: 1 }}>
          <h2 style={{ ...styles.title, fontSize: '16px', marginBottom: '5px' }}>{monitor.nome}</h2>
          <p style={{ margin: 0, color: '#9ca3af', fontSize: '12px' }}>{monitor.descricao}</p>
        </div>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'vehicles' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('vehicles')}
        >
          🚗 Veículos ({vehicles.length})
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'events' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('events')}
        >
          📋 Todos os Eventos ({events.length})
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'vehicles' ? (
          <div>
            {vehicles.map(vehicle => (
              <div
                key={vehicle.device_id}
                style={{
                  ...styles.vehicleCard,
                  cursor: onVehicleSelect ? 'pointer' : 'default',
                }}
                onClick={() => onVehicleSelect && onVehicleSelect(vehicle.device_id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '18px' }}>
                        {vehicle.tipo_veiculo === 'dirijabem' ? '🏁' : '🚗'}
                      </span>
                      <span style={{ color: '#f9fafb', fontWeight: 'bold', fontSize: '14px' }}>
                        {vehicle.device_id}
                      </span>
                    </div>
                    {vehicle.nome_motorista && (
                      <div style={{ marginTop: '4px', color: '#d1d5db', fontSize: '12px' }}>
                        {vehicle.nome_motorista}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontSize: '20px',
                        fontWeight: 'bold',
                        color: getScoreColor(vehicle.score_atual),
                      }}
                    >
                      {vehicle.score_atual.toFixed(1)}
                    </div>
                    <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                      {vehicle.total_eventos_hoje} eventos hoje
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div>
            {/* Critical Events */}
            {groupedEvents.critical.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={styles.categoryTitle}>
                  <span style={{ color: '#dc2626' }}>🚨 Eventos Críticos</span>
                  <span style={styles.categoryCount}>{groupedEvents.critical.length}</span>
                </h3>
                {groupedEvents.critical.map(event => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            )}

            {/* Behavioral Events */}
            {groupedEvents.behavioral.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={styles.categoryTitle}>
                  <span style={{ color: '#f59e0b' }}>⚠️ Eventos Comportamentais</span>
                  <span style={styles.categoryCount}>{groupedEvents.behavioral.length}</span>
                </h3>
                {groupedEvents.behavioral.map(event => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            )}

            {/* Operational Events */}
            {groupedEvents.operational.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={styles.categoryTitle}>
                  <span style={{ color: '#84cc16' }}>📊 Eventos Operacionais</span>
                  <span style={styles.categoryCount}>{groupedEvents.operational.length}</span>
                </h3>
                {groupedEvents.operational.map(event => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            )}

            {events.length === 0 && (
              <div style={{ textAlign: 'center', color: '#9ca3af', padding: '40px 20px' }}>
                Nenhum evento registrado nas últimas horas
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
};

// Event Card Component
const EventCard: React.FC<{ event: Event }> = ({ event }) => {
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
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const eventType = eventTypesCatalog.find(et => et.codigo === event.tipo_evento_codigo);

  return (
    <div
      style={{
        ...styles.eventCard,
        borderLeft: `3px solid ${getSeverityColor(event.severidade)}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
        <span style={{ fontSize: '20px' }}>{eventType?.icone || '•'}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ color: '#f9fafb', fontWeight: 'bold', fontSize: '13px' }}>
              {event.tipo_evento_nome}
            </span>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor: getSeverityColor(event.severidade),
                color: 'white',
                textTransform: 'uppercase',
              }}
            >
              {event.severidade}
            </span>
          </div>
          <div style={{ fontSize: '12px', color: '#d1d5db', marginBottom: '6px' }}>
            <span style={{ fontWeight: 'bold' }}>{event.device_id}</span>
            {event.nome_motorista && <span> - {event.nome_motorista}</span>}
          </div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>
            {formatTimestamp(event.timestamp)}
            {event.velocidade !== undefined && <span> • {event.velocidade} km/h</span>}
            {!event.processado && <span style={{ color: '#f59e0b' }}> • Não processado</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  header: {
    padding: '15px 20px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #374151',
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  title: {
    margin: 0,
    color: '#f9fafb',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  stats: {
    fontSize: '13px',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '15px',
  },
  monitorCard: {
    backgroundColor: '#374151',
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '12px',
    transition: 'all 0.2s ease',
  },
  badge: {
    fontSize: '10px',
    padding: '4px 8px',
    borderRadius: '4px',
    color: 'white',
    fontWeight: 'bold',
  },
  monitorStats: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: '1px solid #4b5563',
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    fontSize: '12px',
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
  },
  tabs: {
    display: 'flex',
    gap: '5px',
    padding: '10px 15px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #374151',
  },
  tab: {
    padding: '8px 16px',
    backgroundColor: 'transparent',
    color: '#9ca3af',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },
  tabActive: {
    backgroundColor: '#374151',
    color: '#f9fafb',
  },
  vehicleCard: {
    backgroundColor: '#374151',
    borderRadius: '6px',
    padding: '12px',
    marginBottom: '8px',
  },
  categoryTitle: {
    margin: '0 0 10px 0',
    color: '#f9fafb',
    fontSize: '14px',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  categoryCount: {
    fontSize: '12px',
    padding: '2px 8px',
    backgroundColor: '#374151',
    borderRadius: '4px',
    color: '#d1d5db',
  },
  eventCard: {
    backgroundColor: '#374151',
    borderRadius: '6px',
    padding: '10px',
    marginBottom: '8px',
  },
};

export default MonitorDashboard;
