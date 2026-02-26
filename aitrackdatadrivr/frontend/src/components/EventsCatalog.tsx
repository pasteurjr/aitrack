import React, { useState } from 'react';
import { eventTypesCatalog, mockEventStats } from '../mockData/mockEvents';
import type { EventType } from '../mockData/mockEvents';

const EventsCatalog: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedEvent, setSelectedEvent] = useState<EventType | null>(null);

  const filteredEvents = selectedCategory === 'all'
    ? eventTypesCatalog
    : eventTypesCatalog.filter(e => e.categoria === selectedCategory);

  const categoryCounts = {
    critical: eventTypesCatalog.filter(e => e.categoria === 'critical').length,
    behavioral: eventTypesCatalog.filter(e => e.categoria === 'behavioral').length,
    operational: eventTypesCatalog.filter(e => e.categoria === 'operational').length,
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#1f2937' }}>
      {!selectedEvent ? (
        <>
          <CatalogHeader stats={mockEventStats} />
          <CategoryFilters
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
            categoryCounts={categoryCounts}
          />
          <EventsList events={filteredEvents} onEventClick={setSelectedEvent} />
        </>
      ) : (
        <EventDetails event={selectedEvent} onBack={() => setSelectedEvent(null)} />
      )}
    </div>
  );
};

// Header with statistics
const CatalogHeader: React.FC<{ stats: typeof mockEventStats }> = ({ stats }) => {
  return (
    <div style={styles.header}>
      <h2 style={styles.title}>📋 Catálogo de Eventos</h2>
      <div style={styles.statsGrid}>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f9fafb' }}>
            {stats.total_eventos_hoje}
          </div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Eventos Hoje</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#dc2626' }}>{stats.criticos}</div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Críticos</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f59e0b' }}>{stats.comportamentais}</div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Comportamentais</div>
        </div>
        <div style={styles.statBox}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#84cc16' }}>{stats.operacionais}</div>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>Operacionais</div>
        </div>
      </div>
    </div>
  );
};

// Category Filters
const CategoryFilters: React.FC<{
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  categoryCounts: { critical: number; behavioral: number; operational: number };
}> = ({ selectedCategory, onCategoryChange, categoryCounts }) => {
  return (
    <div style={styles.filters}>
      <button
        style={{
          ...styles.filterButton,
          ...(selectedCategory === 'all' ? styles.filterButtonActive : {}),
        }}
        onClick={() => onCategoryChange('all')}
      >
        Todos ({categoryCounts.critical + categoryCounts.behavioral + categoryCounts.operational})
      </button>
      <button
        style={{
          ...styles.filterButton,
          ...(selectedCategory === 'critical' ? { ...styles.filterButtonActive, backgroundColor: '#dc2626' } : {}),
        }}
        onClick={() => onCategoryChange('critical')}
      >
        🚨 Críticos ({categoryCounts.critical})
      </button>
      <button
        style={{
          ...styles.filterButton,
          ...(selectedCategory === 'behavioral' ? { ...styles.filterButtonActive, backgroundColor: '#f59e0b' } : {}),
        }}
        onClick={() => onCategoryChange('behavioral')}
      >
        ⚠️ Comportamentais ({categoryCounts.behavioral})
      </button>
      <button
        style={{
          ...styles.filterButton,
          ...(selectedCategory === 'operational' ? { ...styles.filterButtonActive, backgroundColor: '#84cc16' } : {}),
        }}
        onClick={() => onCategoryChange('operational')}
      >
        📊 Operacionais ({categoryCounts.operational})
      </button>
    </div>
  );
};

// Events List
const EventsList: React.FC<{ events: EventType[]; onEventClick: (event: EventType) => void }> = ({
  events,
  onEventClick,
}) => {
  const getCategoryInfo = (category: string) => {
    switch (category) {
      case 'critical':
        return { label: 'Crítico', color: '#dc2626' };
      case 'behavioral':
        return { label: 'Comportamental', color: '#f59e0b' };
      case 'operational':
        return { label: 'Operacional', color: '#84cc16' };
      default:
        return { label: 'Outro', color: '#6b7280' };
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#dc2626';
      case 'high':
        return '#ea580c';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return '#84cc16';
      default:
        return '#6b7280';
    }
  };

  const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  return (
    <div style={styles.content}>
      {events.map(event => {
        const categoryInfo = getCategoryInfo(event.categoria);
        return (
          <div
            key={event.codigo}
            style={{
              ...styles.eventCard,
              borderLeft: `4px solid ${categoryInfo.color}`,
              cursor: 'pointer',
            }}
            onClick={() => onEventClick(event)}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <span style={{ fontSize: '28px', flexShrink: 0 }}>{event.icone}</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <h3 style={{ margin: 0, color: '#f9fafb', fontSize: '15px', fontWeight: 'bold' }}>
                    {event.nome}
                  </h3>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      backgroundColor: categoryInfo.color,
                      color: 'white',
                      textTransform: 'uppercase',
                      fontWeight: 'bold',
                    }}
                  >
                    {categoryInfo.label}
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      backgroundColor: getSeverityColor(event.severidade_padrao),
                      color: 'white',
                      textTransform: 'uppercase',
                      fontWeight: 'bold',
                    }}
                  >
                    {event.severidade_padrao}
                  </span>
                </div>
                <p style={{ margin: '6px 0', color: '#d1d5db', fontSize: '13px', lineHeight: '1.5' }}>
                  {event.descricao}
                </p>
                <div style={{ display: 'flex', gap: '15px', marginTop: '8px', fontSize: '12px' }}>
                  <div style={{ color: '#9ca3af' }}>
                    Código: <span style={{ color: '#d1d5db', fontFamily: 'monospace' }}>{event.codigo}</span>
                  </div>
                  <div style={{ color: '#9ca3af' }}>
                    Resposta: <span style={{ color: '#d1d5db', fontWeight: 'bold' }}>{formatResponseTime(event.tempo_resposta_segundos)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// Event Details
const EventDetails: React.FC<{ event: EventType; onBack: () => void }> = ({ event, onBack }) => {
  const getCategoryInfo = (category: string) => {
    switch (category) {
      case 'critical':
        return { label: 'Crítico', color: '#dc2626', description: 'Eventos que requerem ação imediata (<30s). Usam Redis Pub/Sub para notificação instantânea.' };
      case 'behavioral':
        return { label: 'Comportamental', color: '#f59e0b', description: 'Eventos relacionados ao estilo de condução. Processados via MySQL polling (1-5min aceitável).' };
      case 'operational':
        return { label: 'Operacional', color: '#84cc16', description: 'Eventos de manutenção e eficiência. Polling com intervalo maior (15min-24h).' };
      default:
        return { label: 'Outro', color: '#6b7280', description: '' };
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#dc2626';
      case 'high':
        return '#ea580c';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return '#84cc16';
      default:
        return '#6b7280';
    }
  };

  const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${seconds} segundos`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutos`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} horas`;
    return `${Math.floor(seconds / 86400)} dias`;
  };

  const categoryInfo = getCategoryInfo(event.categoria);

  // Get top occurrences from mock stats
  const topEvent = mockEventStats.top_tipos.find(t => t.tipo === event.codigo);

  return (
    <>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>
          ← Voltar
        </button>
        <h2 style={{ ...styles.title, fontSize: '16px' }}>Detalhes do Evento</h2>
      </div>

      <div style={styles.content}>
        <div style={{ ...styles.eventCard, borderLeft: `4px solid ${categoryInfo.color}` }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <div style={{ fontSize: '64px', marginBottom: '10px' }}>{event.icone}</div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f9fafb', fontSize: '22px', fontWeight: 'bold' }}>
              {event.nome}
            </h3>
            <div style={{ fontSize: '14px', color: '#9ca3af', fontFamily: 'monospace' }}>
              {event.codigo}
            </div>
          </div>

          {/* Badges */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '20px' }}>
            <span
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                borderRadius: '6px',
                backgroundColor: categoryInfo.color,
                color: 'white',
                textTransform: 'uppercase',
                fontWeight: 'bold',
              }}
            >
              {categoryInfo.label}
            </span>
            <span
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                borderRadius: '6px',
                backgroundColor: getSeverityColor(event.severidade_padrao),
                color: 'white',
                textTransform: 'uppercase',
                fontWeight: 'bold',
              }}
            >
              Severidade: {event.severidade_padrao}
            </span>
          </div>

          {/* Description */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>📝 Descrição:</div>
            <p style={{ margin: 0, color: '#d1d5db', fontSize: '14px', lineHeight: '1.6' }}>
              {event.descricao}
            </p>
          </div>

          {/* Category Details */}
          <div style={{ ...styles.infoBox, marginBottom: '15px', borderLeft: `3px solid ${categoryInfo.color}` }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>
              📂 Categoria: <span style={{ color: categoryInfo.color, fontWeight: 'bold' }}>{categoryInfo.label}</span>
            </div>
            <p style={{ margin: 0, color: '#d1d5db', fontSize: '13px', lineHeight: '1.5' }}>
              {categoryInfo.description}
            </p>
          </div>

          {/* Response Time */}
          <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>⏱️ Tempo de Resposta Esperado:</div>
            <div style={{ fontSize: '18px', color: '#f9fafb', fontWeight: 'bold' }}>
              {formatResponseTime(event.tempo_resposta_segundos)}
            </div>
            <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
              {event.tempo_resposta_segundos < 60 && '⚡ Resposta imediata via Redis Pub/Sub'}
              {event.tempo_resposta_segundos >= 60 && event.tempo_resposta_segundos < 900 && '📊 Polling frequente via MySQL'}
              {event.tempo_resposta_segundos >= 900 && '🕐 Polling de longa duração'}
            </div>
          </div>

          {/* Statistics */}
          {topEvent && (
            <div style={{ ...styles.infoBox, marginBottom: '15px' }}>
              <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>📈 Estatísticas Hoje:</div>
              <div style={{ fontSize: '24px', color: '#f9fafb', fontWeight: 'bold' }}>
                {topEvent.count} ocorrências
              </div>
              <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
                Entre os top 5 eventos mais frequentes
              </div>
            </div>
          )}

          {/* Technical Details */}
          <div style={{ ...styles.infoBox, backgroundColor: '#111827' }}>
            <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '10px' }}>🔧 Detalhes Técnicos:</div>
            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
              <tbody>
                <tr style={{ borderBottom: '1px solid #374151' }}>
                  <td style={{ padding: '8px 0', color: '#9ca3af' }}>Código:</td>
                  <td style={{ padding: '8px 0', color: '#d1d5db', fontFamily: 'monospace', textAlign: 'right' }}>
                    {event.codigo}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #374151' }}>
                  <td style={{ padding: '8px 0', color: '#9ca3af' }}>Categoria:</td>
                  <td style={{ padding: '8px 0', color: '#d1d5db', textAlign: 'right' }}>{event.categoria}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #374151' }}>
                  <td style={{ padding: '8px 0', color: '#9ca3af' }}>Severidade Padrão:</td>
                  <td style={{ padding: '8px 0', color: getSeverityColor(event.severidade_padrao), textAlign: 'right', fontWeight: 'bold' }}>
                    {event.severidade_padrao}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #374151' }}>
                  <td style={{ padding: '8px 0', color: '#9ca3af' }}>Tempo de Resposta:</td>
                  <td style={{ padding: '8px 0', color: '#d1d5db', textAlign: 'right' }}>
                    {event.tempo_resposta_segundos}s
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '8px 0', color: '#9ca3af' }}>Cor:</td>
                  <td style={{ padding: '8px 0', textAlign: 'right' }}>
                    <span style={{ display: 'inline-block', width: '20px', height: '20px', backgroundColor: event.cor, borderRadius: '4px', verticalAlign: 'middle' }}></span>
                    <span style={{ marginLeft: '8px', color: '#d1d5db', fontFamily: 'monospace' }}>{event.cor}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
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
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
    marginTop: '15px',
  },
  statBox: {
    backgroundColor: '#374151',
    padding: '10px',
    borderRadius: '6px',
    textAlign: 'center',
  },
  filters: {
    padding: '15px 20px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #374151',
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
  },
  filterButton: {
    padding: '8px 16px',
    backgroundColor: '#374151',
    color: '#d1d5db',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },
  filterButtonActive: {
    backgroundColor: '#3b82f6',
    color: 'white',
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '15px',
  },
  eventCard: {
    backgroundColor: '#374151',
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '12px',
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
  infoBox: {
    backgroundColor: '#1f2937',
    padding: '12px',
    borderRadius: '6px',
  },
};

export default EventsCatalog;
