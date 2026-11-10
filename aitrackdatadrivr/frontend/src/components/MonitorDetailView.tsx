import React, { useEffect, useMemo, useState } from 'react';
import MapComponent from './MapComponent';
import AsyncDataState from './AsyncDataState';
import { eventService, monitorService } from '../services/apiService';
import type { MonitorEvent } from '../types/monitorEvent';
import type { VehicleInMonitor } from '../types/monitor';

interface MonitorDetailViewProps {
  monitorId: number;
  selectedVehicle: VehicleInMonitor | null;
}

const categoryPresentation = {
  critical: { title: '🚨 Eventos Críticos', color: '#dc2626' },
  behavioral: { title: '⚠️ Eventos Comportamentais', color: '#f59e0b' },
  operational: { title: '📊 Eventos Operacionais', color: '#84cc16' },
};

const MonitorDetailView: React.FC<MonitorDetailViewProps> = ({ monitorId, selectedVehicle }) => {
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const vehiclesResponse = await monitorService.getVehicles(monitorId);
        const vehicles = vehiclesResponse.data as VehicleInMonitor[];
        const targetIds = selectedVehicle
          ? new Set([selectedVehicle.device_id])
          : new Set(vehicles.map(vehicle => vehicle.device_id));
        const eventResponses = await Promise.all(
          Array.from(targetIds).map(deviceId => (
            eventService.getAll({ limit: 100, device_id: deviceId })
          )),
        );
        if (active) {
          setEvents(eventResponses
            .flatMap(response => response.data)
            .sort((left, right) => right.timestamp.localeCompare(left.timestamp)));
        }
      } catch {
        if (active) {
          setEvents([]);
          setError('Não foi possível consultar os eventos persistidos deste monitor.');
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, [monitorId, selectedVehicle]);

  const groupedEvents = useMemo(() => ({
    critical: events.filter(event => event.categoria === 'critical'),
    behavioral: events.filter(event => event.categoria === 'behavioral'),
    operational: events.filter(event => event.categoria === 'operational'),
  }), [events]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ flex: 1, minHeight: 0, position: 'relative', borderBottom: '2px solid #374151' }}>
        <MapComponent
          selectedVehicleId={selectedVehicle?.device_id || null}
          selectedUserId={null}
          highlightedEvent={null}
          filterEventsByVehicle={selectedVehicle?.device_id || null}
          onClearEventHighlight={() => {}}
          onClearFilter={() => {}}
        />
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', backgroundColor: '#111827', padding: '15px' }}>
        <h3 style={{ margin: '0 0 15px 0', color: '#f9fafb', fontSize: '16px' }}>
          📊 Eventos persistidos — Monitor #{monitorId}
        </h3>
        {loading ? (
          <AsyncDataState variant="loading" message="Consultando eventos persistidos..." />
        ) : error ? (
          <AsyncDataState variant="error" message={error} />
        ) : (
          (Object.keys(categoryPresentation) as Array<keyof typeof categoryPresentation>).map(category => (
            <EventAnalyzer
              key={category}
              {...categoryPresentation[category]}
              events={groupedEvents[category]}
            />
          ))
        )}
      </div>
    </div>
  );
};

const EventAnalyzer: React.FC<{
  title: string;
  color: string;
  events: MonitorEvent[];
}> = ({ title, color, events }) => {
  const [expanded, setExpanded] = useState(true);
  return (
    <div style={{ ...styles.analyzerCard, borderLeft: `4px solid ${color}`, marginBottom: '15px' }}>
      <button type="button" onClick={() => setExpanded(value => !value)} style={styles.analyzerHeader}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <strong style={{ color: '#f9fafb', fontSize: '14px' }}>{title}</strong>
          <span style={{ ...styles.countBadge, backgroundColor: color }}>{events.length}</span>
        </span>
        <span aria-hidden="true">{expanded ? '▼' : '▶'}</span>
      </button>
      {expanded && (
        <div style={{ marginTop: '15px' }}>
          {events.length === 0 && <p style={styles.empty}>Nenhum evento persistido nesta categoria.</p>}
          {events.slice(0, 20).map(event => (
            <div key={event.id} style={styles.eventItem}>
              <div style={{ flex: 1 }}>
                <strong style={{ color: '#f9fafb', fontSize: '13px' }}>{event.tipo_evento_nome}</strong>
                <div style={{ color: '#9ca3af', fontSize: '11px' }}>{event.device_id}</div>
              </div>
              <time style={{ fontSize: '11px', color: '#9ca3af' }} dateTime={event.timestamp}>
                {new Date(event.timestamp).toLocaleString('pt-BR')}
              </time>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  analyzerCard: { backgroundColor: '#1f2937', borderRadius: '8px', padding: '15px' },
  analyzerHeader: {
    alignItems: 'center', background: 'transparent', border: 0, color: '#9ca3af',
    cursor: 'pointer', display: 'flex', justifyContent: 'space-between', padding: 0, width: '100%',
  },
  countBadge: { fontSize: '11px', padding: '3px 8px', borderRadius: '12px', color: 'white', fontWeight: 'bold' },
  eventItem: {
    alignItems: 'center', backgroundColor: '#374151', borderRadius: '6px', display: 'flex',
    gap: '12px', marginBottom: '8px', padding: '10px',
  },
  empty: { color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' },
};

export default MonitorDetailView;
