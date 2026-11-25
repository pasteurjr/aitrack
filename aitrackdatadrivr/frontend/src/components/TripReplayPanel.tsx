import React, { useEffect, useMemo, useState } from 'react';

import { tripReplayService } from '../services/apiService';
import type { ReplayEvent, TripReplayResponse } from '../types/tripReplay';
import { nextReplayIndex } from './tripReplayControls';

const SPEEDS = [0.5, 1, 2, 4] as const;

function routePoints(data: TripReplayResponse): string {
  const points = [
    ...data.planned_route.geometry.coordinates,
    ...data.positions
      .filter((item) => item.longitude !== undefined && item.latitude !== undefined)
      .map((item) => [item.longitude as number, item.latitude as number] as [number, number]),
  ];
  if (!points.length) return '';
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const scale = (value: number, min: number, max: number) =>
    max === min ? 150 : 15 + ((value - min) / (max - min)) * 270;
  return data.planned_route.geometry.coordinates
    .map(([x, y]) => `${scale(x, minX, maxX)},${300 - scale(y, minY, maxY)}`)
    .join(' ');
}

function eventLabel(event: ReplayEvent): string {
  if (event.kind === 'position') return `Posição · ${event.speed_kmh ?? 0} km/h`;
  if (event.kind === 'episode_started') return `Início · ${event.episode_type}`;
  if (event.kind === 'episode_recovered') return `Recuperação · ${event.episode_type}`;
  return `Execução · ${event.event_type ?? event.to_status}`;
}

export default function TripReplayPanel() {
  const [executionId, setExecutionId] = useState('');
  const [data, setData] = useState<TripReplayResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const visiblePositions = useMemo(() => {
    if (!data) return [];
    const instant = data.timeline[cursor]?.occurred_at;
    return data.positions.filter((position) => !instant || position.occurred_at <= instant);
  }, [data, cursor]);

  useEffect(() => {
    if (!playing || !data || data.timeline.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setCursor((current) => {
        const next = nextReplayIndex(current, data.timeline.length);
        if (next === current) setPlaying(false);
        return next;
      });
    }, 1000 / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, data]);

  const load = async () => {
    if (!executionId.trim()) return;
    setLoading(true);
    setError('');
    setPlaying(false);
    try {
      const response = await tripReplayService.getByExecution(executionId.trim());
      setData(response.data);
      setCursor(0);
    } catch {
      setData(null);
      setError('Não foi possível carregar essa execução de rota.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={styles.root}>
      <header style={styles.header}>
        <div>
          <h2 style={{ margin: 0 }}>Replay de viagem</h2>
          <p style={{ margin: '4px 0 0', color: '#9ca3af' }}>
            Reprodução somente leitura; não cria incidentes nem executa ações.
          </p>
        </div>
        <strong style={styles.badge}>MODO REPLAY</strong>
      </header>
      <section style={styles.search} aria-label="Selecionar execução">
        <input
          aria-label="Identificador da execução"
          value={executionId}
          onChange={(event) => setExecutionId(event.target.value)}
          placeholder="UUID da execução de rota"
          style={styles.input}
        />
        <button onClick={load} disabled={loading || !executionId.trim()} style={styles.button}>
          {loading ? 'Carregando…' : 'Carregar replay'}
        </button>
      </section>
      {error && <div role="alert" style={styles.error}>{error}</div>}
      {!data && !error && <div style={styles.empty}>Informe uma execução para reproduzir a viagem.</div>}
      {data && (
        <>
          <section style={styles.controls} aria-label="Controles do replay">
            <button style={styles.button} onClick={() => setPlaying((value) => !value)}>
              {playing ? 'Pausar' : 'Reproduzir'}
            </button>
            <button style={styles.secondary} onClick={() => { setCursor(0); setPlaying(false); }}>
              Reiniciar
            </button>
            <label>Velocidade{' '}
              <select value={speed} onChange={(event) => setSpeed(Number(event.target.value) as typeof speed)}>
                {SPEEDS.map((value) => <option key={value} value={value}>{value}×</option>)}
              </select>
            </label>
            <input
              aria-label="Posição na linha do tempo"
              type="range"
              min={0}
              max={Math.max(0, data.timeline.length - 1)}
              value={cursor}
              onChange={(event) => { setCursor(Number(event.target.value)); setPlaying(false); }}
              style={{ flex: 1 }}
            />
            <span>{cursor + 1}/{Math.max(1, data.timeline.length)}</span>
          </section>
          <section style={styles.grid}>
            <div style={styles.card}>
              <h3>Rota planejada × realizada</h3>
              <svg viewBox="0 0 300 300" role="img" aria-label="Comparação da rota" style={styles.map}>
                <polyline points={routePoints(data)} fill="none" stroke="#60a5fa" strokeWidth="5" />
                {visiblePositions.map((position, index) => {
                  const actual = data.positions.slice(0, index + 1);
                  const temp = { ...data, planned_route: { ...data.planned_route, geometry: { type: 'LineString' as const, coordinates: actual.map((item) => [item.longitude!, item.latitude!] as [number, number]) } } };
                  const points = routePoints(temp);
                  return index === visiblePositions.length - 1
                    ? <polyline key={position.stable_id} points={points} fill="none" stroke="#10b981" strokeWidth="3" />
                    : null;
                })}
              </svg>
              <p>Corredor: {data.planned_route.corridor_meters} m · versão {data.execution.route_version}</p>
            </div>
            <div style={styles.card}>
              <h3>Linha do tempo</h3>
              <ol style={styles.timeline}>
                {data.timeline.slice(0, cursor + 1).map((event) => (
                  <li key={event.stable_id}>
                    <strong>{eventLabel(event)}</strong><br />
                    <small>{new Date(event.occurred_at).toLocaleString('pt-BR')}</small>
                  </li>
                ))}
              </ol>
              {data.truncated && <p role="status">Resultado limitado a {data.position_limit} posições.</p>}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: { flex: 1, overflow: 'auto', padding: 24, color: '#e5e7eb', background: '#111827' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  badge: { color: '#fbbf24', border: '1px solid #f59e0b', borderRadius: 999, padding: '7px 12px' },
  search: { display: 'flex', gap: 10, margin: '24px 0' },
  input: { flex: 1, padding: 10, background: '#1f2937', color: 'white', border: '1px solid #4b5563', borderRadius: 6 },
  button: { padding: '9px 14px', background: '#059669', color: 'white', border: 0, borderRadius: 6, cursor: 'pointer' },
  secondary: { padding: '9px 14px', background: '#374151', color: 'white', border: 0, borderRadius: 6 },
  error: { padding: 16, background: '#7f1d1d', borderRadius: 6 },
  empty: { padding: 40, textAlign: 'center', color: '#9ca3af', border: '1px dashed #4b5563' },
  controls: { display: 'flex', alignItems: 'center', gap: 12, padding: 12, background: '#1f2937', borderRadius: 8 },
  grid: { display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(300px, 420px)', gap: 16, marginTop: 16 },
  card: { background: '#1f2937', borderRadius: 8, padding: 16 },
  map: { width: '100%', maxHeight: 430, background: '#0f172a', borderRadius: 6 },
  timeline: { maxHeight: 400, overflow: 'auto', paddingLeft: 24 },
};
