import React, { useState } from 'react';
import MapComponent from './MapComponent';
import { mockEvents, eventTypesCatalog } from '../mockData/mockEvents';
import type { VehicleInMonitor } from '../mockData/mockMonitors';

interface MonitorDetailViewProps {
  monitorId: number;
  vehicles: VehicleInMonitor[];
  selectedVehicle: VehicleInMonitor | null;
}

const MonitorDetailView: React.FC<MonitorDetailViewProps> = ({ monitorId, vehicles, selectedVehicle }) => {
  const [highlightedEventIndex, setHighlightedEventIndex] = useState<number | null>(null);

  // Get events for selected vehicle or all vehicles in monitor
  const getEventsForDisplay = () => {
    if (selectedVehicle) {
      return mockEvents.filter(e => e.device_id === selectedVehicle.device_id);
    }
    const vehicleIds = vehicles.map(v => v.device_id);
    return mockEvents.filter(e => vehicleIds.includes(e.device_id));
  };

  const events = getEventsForDisplay();

  // Group events by category
  const criticalEvents = events.filter(e => e.categoria === 'critical');
  const behavioralEvents = events.filter(e => e.categoria === 'behavioral');
  const operationalEvents = events.filter(e => e.categoria === 'operational');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      {/* TOP: Map Area */}
      <div style={{ height: '50%', position: 'relative', borderBottom: '2px solid #374151' }}>
        <MapComponent
          selectedVehicleId={selectedVehicle?.device_id || null}
          selectedUserId={null}
          highlightedEventIndex={highlightedEventIndex}
          filterEventsByVehicle={selectedVehicle?.device_id || null}
          onClearEventHighlight={() => setHighlightedEventIndex(null)}
          onClearFilter={() => {}}
        />
      </div>

      {/* BOTTOM: Event Analyzers */}
      <div style={{ height: '50%', overflowY: 'auto', backgroundColor: '#111827', padding: '15px' }}>
        <h3 style={{ margin: '0 0 15px 0', color: '#f9fafb', fontSize: '16px' }}>
          📊 Analisadores de Eventos - Monitor #{monitorId}
        </h3>

        {/* Critical Events Analyzer */}
        <EventAnalyzer
          title="🚨 Eventos Críticos"
          count={criticalEvents.length}
          color="#dc2626"
          events={criticalEvents}
        />

        {/* Behavioral Events Analyzer */}
        <EventAnalyzer
          title="⚠️ Eventos Comportamentais"
          count={behavioralEvents.length}
          color="#f59e0b"
          events={behavioralEvents}
        />

        {/* Operational Events Analyzer */}
        <EventAnalyzer
          title="📊 Eventos Operacionais"
          count={operationalEvents.length}
          color="#84cc16"
          events={operationalEvents}
        />
      </div>
    </div>
  );
};

// Event Analyzer Component
const EventAnalyzer: React.FC<{
  title: string;
  count: number;
  color: string;
  events: any[];
}> = ({ title, count, color, events }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={{ ...styles.analyzerCard, borderLeft: `4px solid ${color}`, marginBottom: '15px' }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h4 style={{ margin: 0, color: '#f9fafb', fontSize: '14px' }}>{title}</h4>
          <span style={{ ...styles.countBadge, backgroundColor: color }}>{count}</span>
        </div>
        <span style={{ color: '#9ca3af', fontSize: '18px' }}>{expanded ? '▼' : '▶'}</span>
      </div>

      {expanded && (
        <div style={{ marginTop: '15px' }}>
          {events.length === 0 && (
            <div style={{ color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' }}>
              Nenhum evento nesta categoria
            </div>
          )}
          {events.slice(0, 5).map(event => (
            <div key={event.id} style={styles.eventItem}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px' }}>
                  {eventTypesCatalog.find(et => et.codigo === event.tipo_evento_codigo)?.icone || '•'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#f9fafb', fontSize: '13px', fontWeight: '500' }}>
                    {event.tipo_evento_nome}
                  </div>
                  <div style={{ color: '#9ca3af', fontSize: '11px' }}>
                    {event.device_id} {event.nome_motorista && `- ${event.nome_motorista}`}
                  </div>
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                  {new Date(event.timestamp).toLocaleTimeString('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </div>
          ))}
          {events.length > 5 && (
            <div style={{ marginTop: '10px', color: '#9ca3af', fontSize: '12px', textAlign: 'center' }}>
              + {events.length - 5} eventos a mais
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  analyzerCard: {
    backgroundColor: '#1f2937',
    borderRadius: '8px',
    padding: '15px',
  },
  countBadge: {
    fontSize: '11px',
    padding: '3px 8px',
    borderRadius: '12px',
    color: 'white',
    fontWeight: 'bold',
  },
  eventItem: {
    backgroundColor: '#374151',
    borderRadius: '6px',
    padding: '10px',
    marginBottom: '8px',
  },
};

export default MonitorDetailView;
