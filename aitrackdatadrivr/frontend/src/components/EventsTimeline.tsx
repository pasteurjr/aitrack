import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import { fleetService } from '../services/apiService';
import { behavioralEventId } from '../types/behavioralEvent';
import type { BehavioralEvent } from '../types/behavioralEvent';

interface EventsTimelineProps {
    onEventClick: (event: BehavioralEvent) => void;
}

const EventsTimeline: React.FC<EventsTimelineProps> = ({ onEventClick }) => {
    const [events, setEvents] = useState<BehavioralEvent[]>([]);
    const [deviceQuery, setDeviceQuery] = useState('');
    const [typeFilter, setTypeFilter] = useState('all');
    const [severityFilter, setSeverityFilter] = useState('all');
    const [periodFilter, setPeriodFilter] = useState('all');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [stale, setStale] = useState(false);
    const lastUpdatedRef = useRef<Date | null>(null);
    const hasSuccessfulResponse = useRef(false);

    const fetchEvents = useCallback(async () => {
        try {
            const response = await fleetService.getEvents<BehavioralEvent[]>(50);
            setEvents(response.data);
            setError(false);
            setStale(false);
            hasSuccessfulResponse.current = true;
            lastUpdatedRef.current = new Date();
        } catch (requestError) {
            console.error("Erro ao buscar eventos:", requestError);
            if (hasSuccessfulResponse.current) {
                setStale(true);
            } else {
                setError(true);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchEvents();
        const intervalId = setInterval(fetchEvents, 5000);
        return () => clearInterval(intervalId);
    }, [fetchEvents]);

    const eventLabels: {[key: string]: string} = {
        'harsh_accel': 'Aceleração Brusca',
        'harsh_brake': 'Frenagem Brusca',
        'speeding': 'Excesso de Velocidade',
        'sharp_turn': 'Curva Brusca'
    };

    const getSeverityColor = (severity: string) => {
        if (severity === 'critical') return '#b91c1c';
        if (severity === 'high') return '#ef4444';
        if (severity === 'medium') return '#f59e0b';
        return '#10b981';
    };

    const filteredEvents = useMemo(() => {
        const normalizedDevice = deviceQuery.trim().toLocaleLowerCase('pt-BR');
        const now = Date.now();
        const periodMs = periodFilter === '1h'
            ? 60 * 60 * 1000
            : periodFilter === '24h' ? 24 * 60 * 60 * 1000 : null;

        return events
            .filter(event => {
                const timestamp = new Date(event.timestamp).getTime();
                return (!normalizedDevice || event.device_id.toLocaleLowerCase('pt-BR').includes(normalizedDevice))
                    && (typeFilter === 'all' || event.type === typeFilter)
                    && (severityFilter === 'all' || event.severity === severityFilter)
                    && (periodMs === null || (!Number.isNaN(timestamp) && now - timestamp <= periodMs));
            });
    }, [deviceQuery, events, periodFilter, severityFilter, typeFilter]);

    const filtersActive = Boolean(deviceQuery)
        || typeFilter !== 'all'
        || severityFilter !== 'all'
        || periodFilter !== 'all';

    const clearFilters = () => {
        setDeviceQuery('');
        setTypeFilter('all');
        setSeverityFilter('all');
        setPeriodFilter('all');
    };

    return (
        <div style={styles.container}>
            <h3 style={styles.title}>⏱️ TIMELINE DE EVENTOS</h3>

            <div role="group" aria-label="Filtros da timeline" style={styles.filters}>
                <input
                    aria-label="Filtrar por veículo"
                    value={deviceQuery}
                    onChange={event => setDeviceQuery(event.target.value)}
                    placeholder="Veículo ou dispositivo"
                    style={styles.control}
                />
                <select aria-label="Filtrar por tipo" value={typeFilter} onChange={event => setTypeFilter(event.target.value)} style={styles.control}>
                    <option value="all">Todos os tipos</option>
                    {Object.entries(eventLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <select aria-label="Filtrar por severidade" value={severityFilter} onChange={event => setSeverityFilter(event.target.value)} style={styles.control}>
                    <option value="all">Todas as severidades</option>
                    <option value="critical">Crítica</option>
                    <option value="high">Alta</option>
                    <option value="medium">Média</option>
                    <option value="low">Baixa</option>
                </select>
                <select aria-label="Filtrar por período" value={periodFilter} onChange={event => setPeriodFilter(event.target.value)} style={styles.control}>
                    <option value="all">Todo o período</option>
                    <option value="1h">Última hora</option>
                    <option value="24h">Últimas 24 horas</option>
                </select>
                <button type="button" onClick={clearFilters} disabled={!filtersActive} style={styles.clearButton}>Limpar filtros</button>
            </div>

            {loading ? (
                <AsyncDataState variant="loading" message="Consultando eventos recentes..." />
            ) : error ? (
                <AsyncDataState
                    variant="error"
                    message="Não foi possível consultar a timeline. Nenhum evento foi presumido."
                    onRetry={fetchEvents}
                />
            ) : events.length === 0 ? (
                <AsyncDataState variant="empty" message="Nenhum evento foi registrado no período consultado." />
            ) : filteredEvents.length === 0 ? (
                <AsyncDataState variant="empty" message="Nenhum episódio corresponde aos filtros selecionados." />
            ) : (
              <>
                {stale && (
                    <AsyncDataState
                        variant="stale"
                        compact
                        message={`Falha na atualização. Exibindo a última resposta válida${lastUpdatedRef.current ? ` das ${lastUpdatedRef.current.toLocaleTimeString('pt-BR')}` : ''}.`}
                        onRetry={fetchEvents}
                    />
                )}
                <div role="status" style={styles.resultCount}>
                    {filteredEvents.length} de {events.length} episódios exibidos
                </div>
                <div style={styles.timeline}>
                {filteredEvents.map(event => (
                    <button
                        type="button"
                        aria-label={`Abrir episódio ${eventLabels[event.type] ?? event.type} de ${event.device_id}`}
                        key={behavioralEventId(event)}
                        style={{...styles.eventRow, cursor: 'pointer'}}
                        onClick={() => onEventClick(event)}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4b5563'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#374151'}
                    >
                        <div style={{
                            ...styles.iconBadge,
                            backgroundColor: getSeverityColor(event.severity)
                        }}>
                            {event.icon}
                        </div>

                        <div style={styles.eventContent}>
                            <div style={styles.eventHeader}>
                                <strong>{eventLabels[event.type]}</strong>
                                <span style={styles.eventTime}>
                                    {new Date(event.timestamp).toLocaleTimeString()}
                                </span>
                            </div>

                            <div style={styles.eventDetails}>
                                <span style={styles.deviceId}>{event.device_id}</span>
                                <span style={{
                                    ...styles.severityBadge,
                                    backgroundColor: getSeverityColor(event.severity)
                                }}>
                                    {event.severity === 'critical' ? 'Crítica' :
                                     event.severity === 'high' ? 'Alta' :
                                     event.severity === 'medium' ? 'Média' : 'Baixa'}
                                </span>
                            </div>
                        </div>
                    </button>
                ))}
                </div>
              </>
            )}
        </div>
    );
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        padding: '20px',
        backgroundColor: '#1f2937',
        height: '100%',
        overflowY: 'auto',
    },
    title: {
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: '#10b981',
        borderBottom: '2px solid #374151',
        paddingBottom: '10px',
    },
    filters: { display: 'grid', gap: '7px', marginBottom: '12px' },
    control: { backgroundColor: '#111827', border: '1px solid #4b5563', borderRadius: '5px', color: '#f3f4f6', fontSize: '11px', padding: '7px' },
    clearButton: { backgroundColor: '#374151', border: '1px solid #4b5563', borderRadius: '5px', color: '#f3f4f6', cursor: 'pointer', fontSize: '11px', padding: '7px' },
    resultCount: { color: '#9ca3af', fontSize: '10px', marginBottom: '9px', textAlign: 'right' },
    timeline: {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    eventRow: {
        borderBottom: 'none',
        display: 'flex',
        gap: '12px',
        alignItems: 'flex-start',
        padding: '12px',
        backgroundColor: '#374151',
        borderRadius: '6px',
        borderLeft: '3px solid #10b981',
        borderRight: 'none',
        borderTop: 'none',
        color: 'inherit',
        textAlign: 'left',
        width: '100%',
    },
    iconBadge: {
        width: '36px',
        height: '36px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '18px',
        flexShrink: 0,
    },
    eventContent: {
        flex: 1,
    },
    eventHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '5px',
        fontSize: '14px',
        color: '#f3f4f6',
    },
    eventTime: {
        fontSize: '11px',
        color: '#9ca3af',
    },
    eventDetails: {
        display: 'flex',
        gap: '10px',
        alignItems: 'center',
        fontSize: '12px',
    },
    deviceId: {
        color: '#9ca3af',
    },
    severityBadge: {
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '10px',
        fontWeight: 'bold',
        color: 'white',
    },
};

export default EventsTimeline;
