import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import L from 'leaflet';
import { Circle, CircleMarker, Polygon, Popup, useMap } from 'react-leaflet';
import { geofenceService } from '../services/apiService';
import type {
  GeofenceGeometry,
  GeofenceLiveTarget,
  GeofenceStableState,
  LiveGeofence,
} from '../types/geofence';
import './GeofenceLiveLayer.css';

type LatLngTuple = [number, number];

const STATE_LABELS: Record<GeofenceStableState, string> = {
  inside: 'Dentro', outside: 'Fora', unknown: 'Sem leitura',
};
const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

const polygonPositions = (geometry: GeofenceGeometry): LatLngTuple[] => (
  geometry.type === 'Polygon'
    ? geometry.coordinates[0].map(([longitude, latitude]) => [latitude, longitude])
    : []
);

const formatTimestamp = (value: string | null) => (
  value ? new Date(value).toLocaleString('pt-BR') : 'Nunca avaliado'
);

const scheduleLabel = (target: GeofenceLiveTarget) => {
  if (!target.schedules.length) return '24 horas / 7 dias';
  return target.schedules.map(item => (
    `${DAY_LABELS[item.day_of_week]} ${item.start_time.slice(0, 5)}–${item.end_time.slice(0, 5)}${item.crosses_midnight ? ' (+1 dia)' : ''}`
  )).join(' · ');
};

const targetStateClass = (target: GeofenceLiveTarget) => (
  target.is_violation ? 'violation'
    : target.stable_state === 'unknown' ? 'unknown' : 'normal'
);

const targetStateLabel = (target: GeofenceLiveTarget) => {
  const state = STATE_LABELS[target.stable_state];
  if (!target.policy_active) return `${state} · fora da agenda`;
  if (target.is_violation) return `${state} · violação`;
  return `${state} · normal`;
};

const OperationalPopup: React.FC<{ fence: LiveGeofence }> = ({ fence }) => (
  <Popup>
    <div className="geofence-live-popup">
      <strong>{fence.nome}</strong>
      <span>{fence.regra === 'allowed' ? 'Área permitida' : 'Área proibida'} · versão geométrica {fence.geometry_version}</span>
      {!fence.targets.length && <span>Sem alvos ativos.</span>}
      {fence.targets.map(target => (
        <div key={`${target.assignment_id}-${target.subject_type}-${target.subject_id}`}>
          <b>{target.subject_label || target.target_label || 'Alvo sem nome'}</b>
          <span>{targetStateLabel(target)}</span>
          <span>Agenda: {target.schedule_active ? 'ativa' : 'inativa'} · {scheduleLabel(target)}</span>
          <span>Última avaliação: {formatTimestamp(target.last_evaluated_at)}</span>
          <span>Fonte: {target.last_source || 'sem leitura'}</span>
          {target.active_episode && <span>Episódio ativo desde {formatTimestamp(target.violation_started_at)}</span>}
        </div>
      ))}
    </div>
  </Popup>
);

const GeofenceShape: React.FC<{
  fence: LiveGeofence;
  selected: boolean;
  onSelect: () => void;
}> = ({ fence, selected, onSelect }) => {
  const violation = fence.live_summary.violations > 0;
  const color = violation ? '#dc2626'
    : fence.status !== 'active' ? '#64748b'
      : fence.regra === 'allowed' ? '#2563eb' : '#f97316';
  const pathOptions = {
    color,
    fillColor: color,
    fillOpacity: violation ? 0.25 : 0.1,
    weight: selected ? 5 : violation ? 4 : 2,
    dashArray: fence.status === 'active' ? undefined : '6 6',
  };
  const popup = <OperationalPopup fence={fence} />;
  if (fence.geometry.type === 'Circle') {
    const [longitude, latitude] = fence.geometry.center;
    return (
      <Circle center={[latitude, longitude]} radius={fence.geometry.radius_meters}
        pathOptions={pathOptions} eventHandlers={{ click: onSelect }}>
        {popup}
      </Circle>
    );
  }
  return (
    <Polygon positions={polygonPositions(fence.geometry)} pathOptions={pathOptions}
      eventHandlers={{ click: onSelect }}>
      {popup}
    </Polygon>
  );
};

const GeofenceLiveLayer: React.FC = () => {
  const map = useMap();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [geofences, setGeofences] = useState<LiveGeofence[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const loadSnapshot = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    try {
      const response = await geofenceService.getLiveState();
      setGeofences(response.data.geofences);
      setGeneratedAt(response.data.generated_at);
      setError(null);
    } catch {
      setError('Estado das cercas indisponível. O último snapshot foi preservado.');
    } finally {
      if (initial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSnapshot(true);
    const interval = window.setInterval(() => loadSnapshot(false), 5000);
    return () => window.clearInterval(interval);
  }, [loadSnapshot]);

  useEffect(() => {
    if (!panelRef.current) return;
    L.DomEvent.disableClickPropagation(panelRef.current);
    L.DomEvent.disableScrollPropagation(panelRef.current);
  }, [open]);

  const totals = useMemo(() => geofences.reduce((summary, fence) => ({
    violations: summary.violations + fence.live_summary.violations,
    episodes: summary.episodes + fence.live_summary.active_episodes,
  }), { violations: 0, episodes: 0 }), [geofences]);

  const panel = (
    <div className="geofence-live-control" ref={panelRef}>
      {!open ? (
        <button type="button" className="geofence-live-launcher" onClick={() => setOpen(true)}>
          Cercas ({geofences.length}){totals.violations ? ` · ${totals.violations} violação(ões)` : ''}
        </button>
      ) : (
        <section className="geofence-live-panel" aria-label="Estado ao vivo das cercas" aria-live="polite">
          <header>
            <div><strong>Cercas ao vivo</strong><small>{geofences.length} exibida(s) · atualização a cada 5 s</small></div>
            <button type="button" aria-label="Ocultar estado das cercas" onClick={() => setOpen(false)}>×</button>
          </header>
          {loading && <p className="geofence-live-message">Carregando estado operacional…</p>}
          {error && (
            <div className="geofence-live-message error" role="alert">
              {error}
              <button type="button" onClick={() => loadSnapshot(true)}>Tentar novamente</button>
            </div>
          )}
          {!loading && !error && geofences.length === 0 && (
            <p className="geofence-live-message">Nenhuma cerca operacional cadastrada.</p>
          )}
          {generatedAt && <p className="geofence-live-updated">Snapshot: {formatTimestamp(generatedAt)}</p>}
          <div className="geofence-live-list">
            {geofences.map(fence => (
              <button type="button" key={fence.public_id}
                className={`geofence-live-card ${selectedId === fence.public_id ? 'selected' : ''}`}
                onClick={() => setSelectedId(fence.public_id)}>
                <span className="geofence-live-card-title">
                  <b>{fence.nome}</b>
                  <em>{fence.regra === 'allowed' ? 'Permitida' : 'Proibida'}</em>
                </span>
                <span>{fence.live_summary.targets} alvo(s) · {fence.live_summary.violations} violação(ões)</span>
                {!fence.targets.length && <span>Sem alvos ativos</span>}
                {fence.targets.map(target => (
                  <span className={`geofence-live-target ${targetStateClass(target)}`}
                    key={`${target.assignment_id}-${target.subject_type}-${target.subject_id}`}>
                    <b>{target.subject_label || target.target_label}</b>
                    <i>{targetStateLabel(target)}</i>
                    <small>Agenda {target.schedule_active ? 'ativa' : 'inativa'} · {formatTimestamp(target.last_evaluated_at)}</small>
                    {target.active_episode && <small>Episódio ativo</small>}
                  </span>
                ))}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );

  return (
    <>
      {geofences.map(fence => (
        <React.Fragment key={fence.public_id}>
          <GeofenceShape fence={fence} selected={selectedId === fence.public_id}
            onSelect={() => setSelectedId(fence.public_id)} />
          {fence.targets.filter(target => target.last_position).map(target => (
            <CircleMarker key={`${fence.public_id}-${target.assignment_id}-${target.subject_id}`}
              center={[target.last_position!.latitude, target.last_position!.longitude]}
              radius={target.is_violation ? 7 : 4}
              pathOptions={{
                color: target.is_violation ? '#dc2626' : '#0f766e',
                fillColor: target.is_violation ? '#ef4444' : '#14b8a6',
                fillOpacity: 0.9,
              }}>
              <Popup>{target.subject_label || target.target_label} · {targetStateLabel(target)}</Popup>
            </CircleMarker>
          ))}
        </React.Fragment>
      ))}
      {createPortal(panel, map.getContainer())}
    </>
  );
};

export default GeofenceLiveLayer;
