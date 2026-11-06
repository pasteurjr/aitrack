import React, { useMemo, useState } from 'react';

export type FleetSource = 'tracker' | 'dirijabem' | 'both';
type FleetFilter = 'all' | FleetSource;

export interface UnifiedFleetItem {
  id: string;
  source: FleetSource;
  primaryLabel: string;
  secondaryLabel: string;
  score: number | null;
  trackerDeviceId: string | null;
  dirijabemCodusu: number | null;
  modes: string[];
  lastCommunicationAt: string | null;
}

interface UnifiedFleetPanelProps {
  items: UnifiedFleetItem[];
  selectedItemId: string | null;
  onItemSelect: (item: UnifiedFleetItem) => void;
}

const SOURCE_PRESENTATION: Record<FleetSource, { label: string; icon: string; color: string; background: string }> = {
  tracker: {
    label: 'Tracker',
    icon: '🚗',
    color: '#a7f3d0',
    background: '#065f46',
  },
  dirijabem: {
    label: 'Dirija Bem',
    icon: '🏁',
    color: '#bfdbfe',
    background: '#1e40af',
  },
  both: {
    label: 'Tracker + Dirija Bem',
    icon: '🔗',
    color: '#e9d5ff',
    background: '#6b21a8',
  },
};

const UnifiedFleetPanel: React.FC<UnifiedFleetPanelProps> = ({
  items,
  selectedItemId,
  onItemSelect,
}) => {
  const [filter, setFilter] = useState<FleetFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const counts = useMemo(() => ({
    all: items.length,
    tracker: items.filter(item => item.source === 'tracker' || item.source === 'both').length,
    dirijabem: items.filter(item => item.source === 'dirijabem' || item.source === 'both').length,
  }), [items]);
  const normalizedSearch = normalizeSearch(searchQuery);
  const visibleItems = items.filter(item => {
    const matchesSource = filter === 'all' || item.source === filter || item.source === 'both';
    const searchableText = normalizeSearch([
      item.primaryLabel,
      item.secondaryLabel,
      item.trackerDeviceId,
      item.dirijabemCodusu,
      SOURCE_PRESENTATION[item.source].label,
    ].filter(value => value !== null).join(' '));
    return matchesSource && searchableText.includes(normalizedSearch);
  });

  return (
    <section aria-labelledby="unified-fleet-title" style={styles.container}>
      <div style={styles.header}>
        <div>
          <h3 id="unified-fleet-title" style={styles.title}>FROTA UNIFICADA</h3>
          <span style={styles.subtitle}>Origem preservada em cada item</span>
        </div>
        <span style={styles.totalBadge}>{counts.all}</span>
      </div>

      <div role="group" aria-label="Filtrar frota por fonte" style={styles.filters}>
        <FilterButton label="Todos" count={counts.all} active={filter === 'all'} onClick={() => setFilter('all')} />
        <FilterButton label="Tracker" count={counts.tracker} active={filter === 'tracker'} onClick={() => setFilter('tracker')} />
        <FilterButton label="Dirija Bem" count={counts.dirijabem} active={filter === 'dirijabem'} onClick={() => setFilter('dirijabem')} />
      </div>

      <input
        type="search"
        aria-label="Pesquisar frota unificada"
        value={searchQuery}
        onChange={event => setSearchQuery(event.target.value)}
        placeholder="Buscar nome, placa, device ID ou usuário..."
        style={styles.searchInput}
      />

      <div style={styles.list}>
        {visibleItems.map(item => {
          const source = SOURCE_PRESENTATION[item.source];
          const selected = item.id === selectedItemId;
          return (
            <button
              type="button"
              key={item.id}
              aria-pressed={selected}
              onClick={() => onItemSelect(item)}
              style={{
                ...styles.item,
                borderColor: selected ? source.color : '#4b5563',
                backgroundColor: selected ? '#374151' : '#273244',
              }}
            >
              <div style={styles.itemHeader}>
                <span style={{ ...styles.sourceBadge, color: source.color, backgroundColor: source.background }}>
                  {source.icon} {source.label}
                </span>
                <span style={{ ...styles.score, color: item.score === null ? '#9ca3af' : getScoreColor(item.score) }}>
                  {item.score === null ? 'Score indisponível' : `Score ${item.score.toFixed(1)}`}
                </span>
              </div>
              <strong style={styles.primaryLabel}>{item.primaryLabel}</strong>
              <span style={styles.secondaryLabel}>{item.secondaryLabel}</span>
              <span style={styles.telemetryLabel}>
                Modo: {item.modes.length > 0 ? item.modes.join(' + ') : 'unknown'} · Último contato: {formatLastCommunication(item.lastCommunicationAt)}
              </span>
            </button>
          );
        })}
        {visibleItems.length === 0 && (
          <div role="status" style={styles.emptyState}>
            Nenhum veículo corresponde à pesquisa e ao filtro selecionado.
          </div>
        )}
      </div>
    </section>
  );
};

const FilterButton: React.FC<{
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}> = ({ label, count, active, onClick }) => (
  <button
    type="button"
    aria-pressed={active}
    onClick={onClick}
    style={{
      ...styles.filterButton,
      backgroundColor: active ? '#0f766e' : '#374151',
      color: active ? '#ffffff' : '#d1d5db',
    }}
  >
    {label} ({count})
  </button>
);

function getScoreColor(score: number): string {
  if (score >= 75) return '#34d399';
  if (score >= 50) return '#fbbf24';
  return '#f87171';
}

function normalizeSearch(value: unknown): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .trim();
}

function formatLastCommunication(value: string | null): string {
  if (!value) return 'não informado';
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? 'inválido' : timestamp.toLocaleString('pt-BR');
}

const styles: Record<string, React.CSSProperties> = {
  container: { marginBottom: '25px' },
  header: { alignItems: 'center', display: 'flex', justifyContent: 'space-between', marginBottom: '10px' },
  title: { color: '#10b981', fontSize: '14px', margin: 0 },
  subtitle: { color: '#9ca3af', fontSize: '10px' },
  totalBadge: { backgroundColor: '#111827', borderRadius: '999px', color: '#f9fafb', fontSize: '11px', fontWeight: 700, padding: '4px 8px' },
  filters: { display: 'grid', gap: '6px', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', marginBottom: '10px' },
  filterButton: { border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '10px', padding: '7px 4px' },
  searchInput: { backgroundColor: '#111827', border: '1px solid #4b5563', borderRadius: '6px', color: '#f9fafb', fontSize: '11px', marginBottom: '10px', padding: '9px', width: '100%' },
  list: { display: 'flex', flexDirection: 'column', gap: '7px' },
  item: { border: '1px solid', borderRadius: '7px', color: '#f9fafb', cursor: 'pointer', display: 'flex', flexDirection: 'column', padding: '9px', textAlign: 'left', width: '100%' },
  itemHeader: { alignItems: 'center', display: 'flex', justifyContent: 'space-between', marginBottom: '6px' },
  sourceBadge: { borderRadius: '999px', fontSize: '9px', fontWeight: 800, padding: '3px 7px', textTransform: 'uppercase' },
  score: { fontSize: '10px', fontWeight: 700 },
  primaryLabel: { fontSize: '12px', marginBottom: '2px' },
  secondaryLabel: { color: '#9ca3af', fontSize: '10px' },
  telemetryLabel: { color: '#9ca3af', fontSize: '9px', marginTop: '5px' },
  emptyState: { color: '#9ca3af', fontSize: '11px', padding: '16px 8px', textAlign: 'center' },
};

export default UnifiedFleetPanel;
