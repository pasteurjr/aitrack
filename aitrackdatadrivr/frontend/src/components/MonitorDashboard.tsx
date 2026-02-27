import React, { useState, useEffect } from 'react';
import { monitorService } from '../services/apiService';
import type { Monitor, VehicleInMonitor } from '../mockData/mockMonitors';

interface MonitorDashboardProps {
  onMonitorSelect: (monitorId: number) => void;
  onVehicleSelect: (vehicle: VehicleInMonitor) => void;
  selectedMonitorId: number | null;
}

const MonitorDashboard: React.FC<MonitorDashboardProps> = ({
  onMonitorSelect,
  onVehicleSelect,
  selectedMonitorId,
}) => {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [selectedMonitor, setSelectedMonitor] = useState<Monitor | null>(null);
  const [vehiclesInMonitor, setVehiclesInMonitor] = useState<VehicleInMonitor[]>([]);
  const [loading, setLoading] = useState(true);

  // Load all monitors on mount
  useEffect(() => {
    loadMonitors();
  }, []);

  // Load vehicles when monitor is selected
  useEffect(() => {
    if (selectedMonitorId) {
      loadMonitorDetails(selectedMonitorId);
    } else {
      setSelectedMonitor(null);
      setVehiclesInMonitor([]);
    }
  }, [selectedMonitorId]);

  const loadMonitors = async () => {
    try {
      const response = await monitorService.getAll();
      setMonitors(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro carregando monitores:', error);
      setLoading(false);
    }
  };

  const loadMonitorDetails = async (monitorId: number) => {
    try {
      const [monitorResponse, vehiclesResponse] = await Promise.all([
        monitorService.getById(monitorId),
        monitorService.getVehicles(monitorId)
      ]);
      setSelectedMonitor(monitorResponse.data);
      setVehiclesInMonitor(vehiclesResponse.data);
    } catch (error) {
      console.error('Erro carregando detalhes do monitor:', error);
    }
  };

  const handleBack = () => {
    onMonitorSelect(null as any);
  };

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#1f2937' }}>
        <div style={{ color: '#9ca3af', fontSize: '14px' }}>Carregando monitores...</div>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1f2937' }}>
      {!selectedMonitor ? (
        <MonitorList monitors={monitors} onMonitorClick={onMonitorSelect} />
      ) : (
        <VehicleList
          monitor={selectedMonitor}
          vehicles={vehiclesInMonitor}
          onVehicleClick={onVehicleSelect}
          onBack={handleBack}
        />
      )}
    </div>
  );
};

// Monitor List View
const MonitorList: React.FC<{ monitors: Monitor[]; onMonitorClick: (id: number) => void }> = ({
  monitors,
  onMonitorClick,
}) => {
  return (
    <>
      <div style={styles.header}>
        <h2 style={styles.title}>🤖 Monitores AI</h2>
        <div style={styles.stats}>
          <span style={{ color: '#10b981' }}>{monitors.filter(m => m.ativo).length} Ativos</span>
        </div>
      </div>

      <div style={styles.content}>
        {monitors.map(monitor => (
          <div
            key={monitor.id}
            style={{
              ...styles.monitorCard,
              opacity: monitor.ativo ? 1 : 0.5,
              cursor: 'pointer',
            }}
            onClick={() => monitor.ativo && onMonitorClick(monitor.id)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div
                style={{
                  fontSize: '24px',
                  fontWeight: 'bold',
                  color: monitor.ativo ? '#10b981' : '#6b7280',
                }}
              >
                #{monitor.id}
              </div>
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: 0, color: '#f9fafb', fontSize: '16px' }}>{monitor.nome}</h3>
              </div>
              {monitor.ativo && (
                <span style={{ ...styles.badge, backgroundColor: '#10b981' }}>ATIVO</span>
              )}
              {!monitor.ativo && (
                <span style={{ ...styles.badge, backgroundColor: '#6b7280' }}>INATIVO</span>
              )}
            </div>

            <p style={{ margin: '8px 0', color: '#d1d5db', fontSize: '13px' }}>
              {monitor.descricao}
            </p>

            <div style={styles.monitorStats}>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Veículos:</span>
                <span style={{ color: '#f9fafb', fontWeight: 'bold' }}>{monitor.veiculos_monitorados}</span>
              </div>
              <div style={styles.statItem}>
                <span style={{ color: '#9ca3af' }}>Análise:</span>
                <span style={{ color: '#f9fafb' }}>{monitor.intervalo_analise / 60} min</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
};

// Vehicle List with Status Badges
const VehicleList: React.FC<{
  monitor: Monitor;
  vehicles: VehicleInMonitor[];
  onVehicleClick: (vehicle: VehicleInMonitor) => void;
  onBack: () => void;
}> = ({ monitor, vehicles, onVehicleClick, onBack }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ok':
        return { color: '#10b981', label: 'OK', blink: false };
      case 'warning':
        return { color: '#f59e0b', label: 'ALERTA', blink: false };
      case 'critical':
        return { color: '#dc2626', label: 'CRÍTICO', blink: true };
      default:
        return { color: '#6b7280', label: '?', blink: false };
    }
  };

  return (
    <>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>
          ← Voltar
        </button>
        <div>
          <h2 style={{ ...styles.title, fontSize: '16px', marginBottom: '4px' }}>{monitor.nome}</h2>
          <p style={{ margin: 0, color: '#9ca3af', fontSize: '12px' }}>
            {vehicles.length} veículos monitorados
          </p>
        </div>
      </div>

      <div style={styles.content}>
        {vehicles.map(vehicle => {
          const badge = getStatusBadge(vehicle.status);
          return (
            <div
              key={vehicle.device_id}
              style={{
                ...styles.vehicleCard,
                cursor: 'pointer',
              }}
              onClick={() => onVehicleClick(vehicle)}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '18px' }}>
                      {vehicle.tipo_veiculo === 'dirijabem' ? '🏁' : '🚗'}
                    </span>
                    <span style={{ color: '#f9fafb', fontWeight: 'bold', fontSize: '14px' }}>
                      {vehicle.device_id}
                    </span>
                  </div>
                  {vehicle.nome_motorista && (
                    <div style={{ marginLeft: '26px', color: '#d1d5db', fontSize: '12px' }}>
                      {vehicle.nome_motorista}
                    </div>
                  )}
                  <div style={{ marginLeft: '26px', color: '#9ca3af', fontSize: '11px', marginTop: '2px' }}>
                    Score: {vehicle.score_atual.toFixed(1)} • {vehicle.total_eventos_hoje} eventos
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      ...styles.statusBadge,
                      backgroundColor: badge.color,
                      animation: badge.blink ? 'blink 1s infinite' : 'none',
                    }}
                  >
                    {badge.label}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* CSS for blinking animation */}
      <style>{`
        @keyframes blink {
          0%, 50%, 100% { opacity: 1; }
          25%, 75% { opacity: 0.3; }
        }
      `}</style>
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
  stats: {
    fontSize: '13px',
    marginTop: '8px',
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
    gridTemplateColumns: 'repeat(2, 1fr)',
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
    marginBottom: '10px',
  },
  vehicleCard: {
    backgroundColor: '#374151',
    borderRadius: '6px',
    padding: '12px',
    marginBottom: '8px',
    transition: 'all 0.2s ease',
  },
  statusBadge: {
    fontSize: '10px',
    padding: '6px 12px',
    borderRadius: '12px',
    color: 'white',
    fontWeight: 'bold',
    textTransform: 'uppercase',
    display: 'inline-block',
  },
};

export default MonitorDashboard;
