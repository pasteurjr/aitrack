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
import type { VehicleInMonitor } from './types/monitor';
import type { BehavioralEvent } from './types/behavioralEvent';
import './App.css';

type ViewMode = 'dashboard' | 'timeline' | 'analytics' | 'monitors' | 'alerts' | 'events';

function App() {
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [highlightedEvent, setHighlightedEvent] = useState<BehavioralEvent | null>(null);
  const [filterEventsByVehicle, setFilterEventsByVehicle] = useState<string | null>(null);

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
      {/* Top Navigation Bar */}
      <div style={styles.navbar}>
        <div style={styles.brand}>
          <h1 style={styles.logo}>AITrack + DataDrivr</h1>
          <OperationModeBadge />
        </div>
        <div style={styles.navTabs}>
          <button
            style={{...styles.navTab, ...(viewMode === 'dashboard' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            style={{...styles.navTab, ...(viewMode === 'timeline' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('timeline')}
          >
            ⏱️ Timeline
          </button>
          <button
            style={{...styles.navTab, ...(viewMode === 'analytics' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('analytics')}
          >
            📈 Análises
          </button>
          <button
            style={{...styles.navTab, ...(viewMode === 'monitors' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('monitors')}
          >
            🤖 Monitores AI
          </button>
          <button
            style={{...styles.navTab, ...(viewMode === 'alerts' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('alerts')}
          >
            🚨 Incidentes
          </button>
          <button
            style={{...styles.navTab, ...(viewMode === 'events' ? styles.navTabActive : {})}}
            onClick={() => setViewMode('events')}
          >
            📋 Eventos
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
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
            <AlertsPanel onVehicleSelect={setSelectedVehicleId} />
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
                }}
              />
              <div style={{ flex: 1, minHeight: 0 }}>
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
              </div>
            </div>
          )}
        </div>
      </div>
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
    backgroundColor: '#10b981',
    color: 'white',
  },
  sidebar: {
    width: '350px',
    backgroundColor: '#1f2937',
    overflowY: 'auto',
  },
};

export default App;
