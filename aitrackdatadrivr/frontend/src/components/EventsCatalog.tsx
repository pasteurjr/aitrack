import React, { useEffect, useMemo, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import { eventService } from '../services/apiService';
import type { EventCategory, EventStats, EventType } from '../types/monitorEvent';

const EMPTY_STATS: EventStats = {
  total_eventos_hoje: 0,
  por_tipo: {},
  por_categoria: {},
};

const categoryInfo: Record<EventCategory, { label: string; color: string }> = {
  critical: { label: 'Crítico', color: '#dc2626' },
  behavioral: { label: 'Comportamental', color: '#f59e0b' },
  operational: { label: 'Operacional', color: '#84cc16' },
};

const EventsCatalog: React.FC = () => {
  const [catalog, setCatalog] = useState<EventType[]>([]);
  const [stats, setStats] = useState<EventStats>(EMPTY_STATS);
  const [selectedCategory, setSelectedCategory] = useState<'all' | EventCategory>('all');
  const [selectedEvent, setSelectedEvent] = useState<EventType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [catalogResponse, statsResponse] = await Promise.all([
        eventService.getCatalog(), eventService.getStats(),
      ]);
      setCatalog(catalogResponse.data);
      setStats(statsResponse.data);
    } catch {
      setCatalog([]);
      setStats(EMPTY_STATS);
      setError('Não foi possível consultar o catálogo e as estatísticas persistidas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filteredEvents = useMemo(() => (
    selectedCategory === 'all'
      ? catalog
      : catalog.filter(event => event.categoria === selectedCategory)
  ), [catalog, selectedCategory]);

  if (loading) return <AsyncDataState variant="loading" message="Consultando catálogo persistido..." />;
  if (error) return <AsyncDataState variant="error" message={error} onRetry={load} />;
  if (!catalog.length) return <AsyncDataState variant="empty" message="Nenhum tipo de evento está cadastrado." />;

  if (selectedEvent) {
    return <EventDetails event={selectedEvent} count={stats.por_tipo[selectedEvent.codigo] || 0} onBack={() => setSelectedEvent(null)} />;
  }

  return (
    <div style={styles.root}>
      <CatalogHeader stats={stats} />
      <div style={styles.filters}>
        <FilterButton active={selectedCategory === 'all'} onClick={() => setSelectedCategory('all')}>
          Todos ({catalog.length})
        </FilterButton>
        {(Object.keys(categoryInfo) as EventCategory[]).map(category => (
          <FilterButton key={category} active={selectedCategory === category}
            onClick={() => setSelectedCategory(category)} activeColor={categoryInfo[category].color}>
            {categoryInfo[category].label} ({catalog.filter(event => event.categoria === category).length})
          </FilterButton>
        ))}
      </div>
      <div style={styles.content}>
        {filteredEvents.map(event => (
          <button type="button" key={event.codigo} style={{ ...styles.eventCard, borderLeft: `4px solid ${event.cor}` }}
            onClick={() => setSelectedEvent(event)}>
            <span style={{ fontSize: '28px' }}>{event.icone || '•'}</span>
            <span style={{ flex: 1, textAlign: 'left' }}>
              <strong style={{ color: '#f9fafb' }}>{event.nome}</strong>
              <small style={styles.description}>{event.descricao}</small>
              <small style={styles.meta}>{event.codigo} · {categoryInfo[event.categoria].label} · {event.severidade_padrao}</small>
            </span>
            <strong style={{ color: event.cor }}>{stats.por_tipo[event.codigo] || 0} hoje</strong>
          </button>
        ))}
      </div>
    </div>
  );
};

const CatalogHeader: React.FC<{ stats: EventStats }> = ({ stats }) => (
  <header style={styles.header}>
    <h2 style={styles.title}>📋 Catálogo operacional de eventos</h2>
    <div style={styles.statsGrid}>
      <Stat value={stats.total_eventos_hoje} label="Eventos hoje" color="#f9fafb" />
      <Stat value={stats.por_categoria.critical || 0} label="Críticos" color="#dc2626" />
      <Stat value={stats.por_categoria.behavioral || 0} label="Comportamentais" color="#f59e0b" />
      <Stat value={stats.por_categoria.operational || 0} label="Operacionais" color="#84cc16" />
    </div>
  </header>
);

const Stat: React.FC<{ value: number; label: string; color: string }> = ({ value, label, color }) => (
  <div style={styles.statBox}><strong style={{ fontSize: '20px', color }}>{value}</strong><small>{label}</small></div>
);

const FilterButton: React.FC<{
  active: boolean; onClick: () => void; activeColor?: string; children: React.ReactNode;
}> = ({ active, onClick, activeColor = '#10b981', children }) => (
  <button type="button" onClick={onClick} style={{ ...styles.filterButton, backgroundColor: active ? activeColor : '#374151' }}>
    {children}
  </button>
);

const EventDetails: React.FC<{ event: EventType; count: number; onBack: () => void }> = ({ event, count, onBack }) => (
  <div style={styles.root}>
    <header style={styles.header}>
      <button type="button" onClick={onBack} style={styles.backButton}>← Voltar</button>
      <h2 style={styles.title}>Detalhes do tipo de evento</h2>
    </header>
    <div style={styles.content}>
      <article style={{ ...styles.detailsCard, borderLeft: `4px solid ${event.cor}` }}>
        <div style={{ fontSize: '52px' }}>{event.icone || '•'}</div>
        <h3 style={{ color: '#f9fafb', fontSize: '22px', margin: '8px 0' }}>{event.nome}</h3>
        <code>{event.codigo}</code>
        <p style={{ color: '#d1d5db' }}>{event.descricao}</p>
        <p style={styles.meta}>Categoria: {categoryInfo[event.categoria].label}</p>
        <p style={styles.meta}>Severidade padrão: {event.severidade_padrao}</p>
        <p style={{ color: event.cor, fontSize: '22px', fontWeight: 700 }}>{count} ocorrência(s) hoje</p>
      </article>
    </div>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  root: { height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1f2937' },
  header: { padding: '20px', backgroundColor: '#111827', borderBottom: '1px solid #374151' },
  title: { margin: '0 0 14px', color: '#f9fafb', fontSize: '20px' },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' },
  statBox: { display: 'flex', flexDirection: 'column', padding: '10px', backgroundColor: '#1f2937', borderRadius: '6px', color: '#9ca3af' },
  filters: { display: 'flex', gap: '8px', padding: '12px 20px', flexWrap: 'wrap' },
  filterButton: { border: 0, borderRadius: '5px', color: 'white', cursor: 'pointer', padding: '8px 12px' },
  content: { overflowY: 'auto', padding: '15px 20px', flex: 1 },
  eventCard: { alignItems: 'center', backgroundColor: '#111827', border: 0, borderRadius: '8px', color: '#d1d5db', cursor: 'pointer', display: 'flex', gap: '12px', marginBottom: '10px', padding: '14px', width: '100%' },
  description: { color: '#d1d5db', display: 'block', marginTop: '5px' },
  meta: { color: '#9ca3af', display: 'block', marginTop: '6px' },
  backButton: { background: '#374151', border: 0, borderRadius: '5px', color: 'white', cursor: 'pointer', padding: '7px 12px' },
  detailsCard: { backgroundColor: '#111827', borderRadius: '8px', padding: '24px' },
};

export default EventsCatalog;
