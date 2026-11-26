import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import BehavioralDashboard from './components/BehavioralDashboard';
import EventsTimeline from './components/EventsTimeline';
import VehicleAnalytics from './components/VehicleAnalytics';
import MonitorDashboard from './components/MonitorDashboard';
import MonitorDetailView from './components/MonitorDetailView';
import AlertsPanel from './components/AlertsPanel';
import EventsCatalog from './components/EventsCatalog';
import OperationModeBadge from './components/OperationModeBadge';
import VehicleDetailHeader from './components/VehicleDetailHeader';
import VehicleSensorsPanel from './components/VehicleSensorsPanel';
import AgentConfigurationPanel from './components/AgentConfigurationPanel';
import AgentRunsPanel from './components/AgentRunsPanel';
import InternalNotificationsPanel from './components/InternalNotificationsPanel';
import TripReplayPanel from './components/TripReplayPanel';
import HealthIntegrationsPanel from './components/HealthIntegrationsPanel';
import { useAuth } from './components/AuthGate';
import type { VehicleInMonitor } from './types/monitor';
import type { BehavioralEvent } from './types/behavioralEvent';
import './App.css';

type ViewMode = 'dashboard' | 'timeline' | 'analytics' | 'monitors' | 'agents' | 'agentRuns' | 'notifications' | 'replay' | 'alerts' | 'events' | 'health';

function App() {
  const auth = useAuth();
  const can = (permission: string) => !auth || auth.permissions.includes(permission);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [highlightedEvent, setHighlightedEvent] = useState<BehavioralEvent | null>(null);
  const [filterEventsByVehicle, setFilterEventsByVehicle] = useState<string | null>(null);
  const [detailMode, setDetailMode] = useState<'map' | 'sensors'>('map');
  const [notificationIncidentId,setNotificationIncidentId]=useState<number|null>(null);

  // Monitor state
  const [selectedMonitorId, setSelectedMonitorId] = useState<number | null>(null);
  const [selectedMonitorVehicle, setSelectedMonitorVehicle] = useState<VehicleInMonitor | null>(null);

  const handleEventClick = (event: BehavioralEvent) => {
    setHighlightedEvent(event);
    setSelectedVehicleId(event.device_id);
    setSelectedUserId(null);
    setFilterEventsByVehicle(null); // Limpa filtro
    // NÃO muda viewMode - mantém timeline aberta
  };

  const handleVehicleEventsClick = (deviceId: string) => {
    console.log('Clicou no veículo:', deviceId);
    setFilterEventsByVehicle(deviceId);
    setSelectedVehicleId(deviceId);
    setHighlightedEvent(null);
    setViewMode('dashboard');
  };

  const handleMonitorSelect = (monitorId: number | null) => {
    setSelectedMonitorId(monitorId);
    setSelectedMonitorVehicle(null);
    if (!monitorId) {
      // Clear vehicle selection when going back to monitor list
      setSelectedVehicleId(null);
    }
  };

  const handleMonitorVehicleSelect = (vehicle: VehicleInMonitor) => {
    setSelectedMonitorVehicle(vehicle);
    setSelectedVehicleId(vehicle.device_id);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100%' }}>
      <a className="skip-link" href="#main-content">Pular para o conteúdo principal</a>
      {/* Top Navigation Bar */}
      <header style={styles.navbar}>
        <div style={styles.brand}>
          <h1 style={styles.logo}>AITrack + DataDrivr</h1>
          <OperationModeBadge />
        </div>
        <nav aria-label="Navegação principal" style={styles.navTabs}>
          {can('fleet.read') && <button
            aria-current={viewMode === 'replay' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'replay' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('replay')}
          >
            ▶ Replay
          </button>}
          {can('incident.read') && <button
            aria-current={viewMode === 'notifications' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'notifications' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('notifications')}
          >
            🔔 Notificações
          </button>}
          {can('agent.configure') && <button
            aria-current={viewMode === 'agentRuns' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'agentRuns' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('agentRuns')}
          >
            🧾 Execuções IA
          </button>}
          {can('agent.configure') && <button
            aria-current={viewMode === 'agents' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'agents' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('agents')}
          >
            🧠 Agentes
          </button>}
          {can('fleet.read') && <button
            aria-current={viewMode === 'dashboard' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'dashboard' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('dashboard')}
          >
            📊 Dashboard
          </button>}
          {can('fleet.read') && <button
            aria-current={viewMode === 'timeline' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'timeline' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('timeline')}
          >
            ⏱️ Timeline
          </button>}
          {can('report.read') && <button
            aria-current={viewMode === 'analytics' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'analytics' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('analytics')}
          >
            📈 Análises
          </button>}
          {can('fleet.read') && <button
            aria-current={viewMode === 'monitors' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'monitors' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('monitors')}
          >
            🤖 Monitores AI
          </button>}
          {can('incident.read') && <button
            aria-current={viewMode === 'alerts' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'alerts' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('alerts')}
          >
            🚨 Incidentes
          </button>}
          {can('fleet.read') && <button
            aria-current={viewMode === 'events' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'events' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('events')}
          >
            📋 Eventos
          </button>}
          {can('health.read') && <button
            aria-current={viewMode === 'health' ? 'page' : undefined}
            style={{...styles.navTab, ...(viewMode === 'health' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('health')}
          >
            ♥ Saúde
          </button>}
        </nav>
      </header>

      {/* Main Content */}
        <main id="main-content" tabIndex={-1} style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {viewMode === 'health' ? <HealthIntegrationsPanel /> : viewMode === 'replay' ? <TripReplayPanel /> : viewMode === 'agents' ? <AgentConfigurationPanel /> : viewMode === 'agentRuns' ? <AgentRunsPanel /> : viewMode==='notifications'?<InternalNotificationsPanel onOpenIncident={id=>{setNotificationIncidentId(id);setViewMode('alerts')}}/> : <>
        {/* Left Sidebar - Conditional Content */}
        <div style={styles.sidebar}>
          {viewMode === 'dashboard' && (
            <BehavioralDashboard
              selectedVehicleId={selectedVehicleId}
              onVehicleSelect={setSelectedVehicleId}
              selectedUserId={selectedUserId}
              onUserSelect={setSelectedUserId}
            />
          )}
          {viewMode === 'timeline' && (
            <EventsTimeline onEventClick={handleEventClick} />
          )}
          {viewMode === 'analytics' && (
            <VehicleAnalytics onVehicleClick={handleVehicleEventsClick} />
          )}
          {viewMode === 'monitors' && (
            <MonitorDashboard
              onMonitorSelect={handleMonitorSelect}
              onVehicleSelect={handleMonitorVehicleSelect}
              selectedMonitorId={selectedMonitorId}
            />
          )}
          {viewMode === 'alerts' && (
            <AlertsPanel onVehicleSelect={setSelectedVehicleId} initialIncidentId={notificationIncidentId} />
          )}
          {viewMode === 'events' && (
            <EventsCatalog />
          )}
        </div>

        {/* Main Area - Map or Monitor Detail View */}
        <div style={{ flex: 1, position: 'relative' }}>
          {viewMode === 'monitors' && selectedMonitorId ? (
            <MonitorDetailView
              monitorId={selectedMonitorId}
              selectedVehicle={selectedMonitorVehicle}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <VehicleDetailHeader
                selectedVehicleId={selectedVehicleId}
                selectedUserId={selectedUserId}
                onClear={() => {
                  setFilterEventsByVehicle(null);
                  setHighlightedEvent(null);
                  setSelectedVehicleId(null);
                  setSelectedUserId(null);
                  setDetailMode('map');
                }}
              />
              {(selectedVehicleId !== null || selectedUserId !== null) && (
                <div role="tablist" aria-label="Detalhes do veículo" style={styles.detailTabs}>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={detailMode === 'map'}
                    style={{ ...styles.detailTab, ...(detailMode === 'map' ? styles.detailTabActive : {}) }}
                    onClick={() => setDetailMode('map')}
                  >Mapa e rota</button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={detailMode === 'sensors'}
                    style={{ ...styles.detailTab, ...(detailMode === 'sensors' ? styles.detailTabActive : {}) }}
                    onClick={() => setDetailMode('sensors')}
                  >Sensores</button>
                </div>
              )}
              <div style={{ flex: 1, minHeight: 0 }}>
                {detailMode === 'sensors' ? (
                  <VehicleSensorsPanel selectedVehicleId={selectedVehicleId} selectedUserId={selectedUserId} />
                ) : (
                  <MapComponent
                    selectedVehicleId={selectedVehicleId}
                    selectedUserId={selectedUserId}
                    highlightedEvent={highlightedEvent}
                    filterEventsByVehicle={filterEventsByVehicle}
                    onClearEventHighlight={() => setHighlightedEvent(null)}
                    onClearFilter={() => {
                      setFilterEventsByVehicle(null);
                      setSelectedVehicleId(null);
                      setSelectedUserId(null);
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </div>
        </>}
      </main>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  navbar: {
    height: '60px',
    backgroundColor: '#111827',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 20px',
    borderBottom: '2px solid #374151',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
  },
  logo: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#10b981',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexShrink: 0,
  },
  navTabs: {
    display: 'flex',
    gap: '10px',
  },
  navTab: {
    padding: '10px 20px',
    backgroundColor: '#374151',
    color: '#d1d5db',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },
  navTabActive: {
    backgroundColor: '#065f46',
    color: '#ecfdf5',
  },
  sidebar: {
    width: '350px',
    backgroundColor: '#1f2937',
    overflowY: 'auto',
  },
  detailTabs: {
    backgroundColor: '#111827',
    borderBottom: '1px solid #334155',
    display: 'flex',
    gap: '6px',
    padding: '6px 12px',
  },
  detailTab: {
    backgroundColor: 'transparent',
    borderColor: '#475569',
    borderRadius: '5px',
    borderStyle: 'solid',
    borderWidth: '1px',
    color: '#cbd5e1',
    cursor: 'pointer',
    fontSize: '11px',
    padding: '5px 10px',
  },
  detailTabActive: {
    backgroundColor: '#065f46',
    borderColor: '#10b981',
    color: '#ecfdf5',
  },
};

export default App;
