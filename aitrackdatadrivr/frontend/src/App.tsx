import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import BehavioralDashboard from './components/BehavioralDashboard';
import EventsTimeline from './components/EventsTimeline';
import VehicleAnalytics from './components/VehicleAnalytics';
import './App.css';

type ViewMode = 'dashboard' | 'timeline' | 'analytics';

function App() {
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);  // NEW: Dirijabem user
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [highlightedEventIndex, setHighlightedEventIndex] = useState<number | null>(null);
  const [filterEventsByVehicle, setFilterEventsByVehicle] = useState<string | null>(null);

  const handleEventClick = (eventIndex: number) => {
    console.log('Clicou no evento:', eventIndex);
    setHighlightedEventIndex(eventIndex);
    setSelectedVehicleId(null); // Limpa seleção de veículo
    setFilterEventsByVehicle(null); // Limpa filtro
    // NÃO muda viewMode - mantém timeline aberta
  };

  const handleVehicleEventsClick = (deviceId: string) => {
    console.log('Clicou no veículo:', deviceId);
    setFilterEventsByVehicle(deviceId);
    setSelectedVehicleId(deviceId);
    setHighlightedEventIndex(null); // Limpa evento destacado
    setViewMode('dashboard'); // Volta para o dashboard/mapa
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100%' }}>
      {/* Top Navigation Bar */}
      <div style={styles.navbar}>
        <h1 style={styles.logo}>AITrack + DataDrivr</h1>
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
        </div>

        {/* Main Map Area */}
        <div style={{ flex: 1, position: 'relative' }}>
          <MapComponent
            selectedVehicleId={selectedVehicleId}
            selectedUserId={selectedUserId}
            highlightedEventIndex={highlightedEventIndex}
            filterEventsByVehicle={filterEventsByVehicle}
            onClearEventHighlight={() => setHighlightedEventIndex(null)}
            onClearFilter={() => {
              setFilterEventsByVehicle(null);
              setSelectedVehicleId(null);
              setSelectedUserId(null);
            }}
          />
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
