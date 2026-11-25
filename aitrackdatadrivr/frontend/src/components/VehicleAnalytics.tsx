import React, { useCallback, useEffect, useRef, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import { analyticsService } from '../services/apiService';
import type { AnalyticsSource, BehaviorAnalyticsResponse } from '../types/analytics';

interface VehicleAnalyticsProps {
    onVehicleClick: (deviceId: string) => void;
}

const VehicleAnalytics: React.FC<VehicleAnalyticsProps> = ({ onVehicleClick }) => {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const asLocalInput = (value: Date) => {
        const offset = value.getTimezoneOffset() * 60_000;
        return new Date(value.getTime() - offset).toISOString().slice(0, 16);
    };
    const [from, setFrom] = useState(asLocalInput(yesterday));
    const [to, setTo] = useState(asLocalInput(now));
    const [sources, setSources] = useState<AnalyticsSource[]>(['tracker', 'dirijabem']);
    const [analytics, setAnalytics] = useState<BehaviorAnalyticsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [stale, setStale] = useState(false);
    const hasSuccessfulResponse = useRef(false);
    const lastUpdatedRef = useRef<Date | null>(null);

    const fetchData = useCallback(async () => {
        try {
            const response = await analyticsService.getBehavior({
                from,
                to,
                timezone: 'America/Sao_Paulo',
                sources,
                comparison: 'previous',
            });
            setAnalytics(response.data);
            setError(false);
            setStale(false);
            hasSuccessfulResponse.current = true;
            lastUpdatedRef.current = new Date();
        } catch (requestError) {
            console.error("Erro ao buscar dados:", requestError);
            if (hasSuccessfulResponse.current) {
                setStale(true);
            } else {
                setError(true);
            }
        } finally {
            setLoading(false);
        }
    }, [from, to, sources]);

    useEffect(() => {
        fetchData();
        // Análise histórica só muda quando os filtros mudam ou o operador atualiza.
    }, [fetchData]);

    // Calcular distribuição de eventos por tipo
    const eventsByType = (analytics?.current.by_type || []).reduce((acc, event) => {
        acc[event.event_type] = (acc[event.event_type] || 0) + event.total;
        return acc;
    }, {} as {[key: string]: number});

    // Calcular distribuição de eventos por veículo
    const eventsByVehicle = (analytics?.current.by_vehicle || []).reduce((acc, event) => {
        const key = `${event.source}:${event.device_id || 'sem-identificador'}`;
        acc[key] = (acc[key] || 0) + event.total;
        return acc;
    }, {} as {[key: string]: number});

    const eventLabels: {[key: string]: string} = {
        'harsh_accel': 'Aceleração Brusca',
        'harsh_brake': 'Frenagem Brusca',
        'speeding': 'Excesso de Velocidade',
        'sharp_turn': 'Curva Brusca'
    };

    const eventIcons: {[key: string]: string} = {
        'harsh_accel': '⚡',
        'harsh_brake': '🛑',
        'speeding': '🚨',
        'sharp_turn': '↪️'
    };

    const totalEvents = Object.values(eventsByType).reduce((a, b) => a + b, 0);

    // Top 5 veículos com mais eventos
    const topVehiclesByEvents = Object.entries(eventsByVehicle)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    return (
        <div style={styles.container}>
            <h3 style={styles.title}>📈 ANÁLISES COMPORTAMENTAIS</h3>

            <div style={styles.section} aria-label="Filtros da análise">
                <label>De <input type="datetime-local" value={from} onChange={event => setFrom(event.target.value)} /></label>
                <label> Até <input type="datetime-local" value={to} onChange={event => setTo(event.target.value)} /></label>
                {(['tracker', 'dirijabem'] as AnalyticsSource[]).map(source => (
                    <label key={source} style={{ marginLeft: 8 }}>
                        <input
                            type="checkbox"
                            checked={sources.includes(source)}
                            disabled={sources.length === 1 && sources.includes(source)}
                            onChange={() => setSources(current => current.includes(source)
                                ? current.filter(item => item !== source)
                                : [...current, source])}
                        /> {source === 'tracker' ? 'Tracker' : 'Dirija Bem'}
                    </label>
                ))}
                <button onClick={fetchData} disabled={!sources.length} style={{ marginLeft: 8 }}>Atualizar</button>
                <div style={{ marginTop: 8, color: '#9ca3af' }}>
                    Comparação automática com o período anterior de mesma duração · fuso America/Sao_Paulo
                </div>
            </div>

            {loading ? (
                <AsyncDataState variant="loading" message="Calculando indicadores comportamentais..." />
            ) : error ? (
                <AsyncDataState
                    variant="error"
                    message="Não foi possível carregar scores e eventos. Nenhum indicador foi calculado com dados incompletos."
                    onRetry={fetchData}
                />
            ) : totalEvents === 0 ? (
                <AsyncDataState variant="empty" message="Não existem eventos persistidos nesse período e nas fontes selecionadas." />
            ) : (
              <>
                {stale && (
                    <AsyncDataState
                        variant="stale"
                        compact
                        message={`Falha na atualização. Exibindo a última resposta válida${lastUpdatedRef.current ? ` das ${lastUpdatedRef.current.toLocaleTimeString('pt-BR')}` : ''}.`}
                        onRetry={fetchData}
                    />
                )}

            {/* Distribuição de Eventos por Tipo */}
            <div style={styles.section}>
                <h4 style={styles.sectionTitle}>Eventos por Tipo</h4>
                <div style={{ fontSize: 12, marginBottom: 12 }}>
                    Atual: {analytics?.current.total_events ?? 0} · período anterior: {analytics?.comparison?.total_events ?? 0}
                </div>
                {Object.entries(eventsByType).map(([type, count]) => {
                    const percentage = totalEvents > 0 ? (count / totalEvents) * 100 : 0;
                    return (
                        <div key={type} style={styles.chartRow}>
                            <div style={styles.chartLabel}>
                                <span>{eventIcons[type]} {eventLabels[type]}</span>
                                <span style={styles.chartValue}>{count}</span>
                            </div>
                            <div style={styles.barContainer}>
                                <div
                                    style={{
                                        ...styles.bar,
                                        width: `${percentage}%`,
                                        backgroundColor: getEventColor(type)
                                    }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Top Veículos com Mais Eventos */}
            <div style={styles.section}>
                <h4 style={styles.sectionTitle}>⚠️ Veículos com Mais Eventos (clique para ver)</h4>
                {topVehiclesByEvents.map(([vehicleKey, count], index) => {
                    const [source, deviceId] = vehicleKey.split(':', 2);
                    return (
                        <div
                            key={vehicleKey}
                            style={{...styles.vehicleEventRow, cursor: 'pointer'}}
                            onClick={() => deviceId !== 'sem-identificador' && onVehicleClick(deviceId)}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4b5563'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#1f2937'}
                        >
                            <div style={styles.rank}>{index + 1}</div>
                            <div style={styles.vehicleEventInfo}>
                                <strong>{deviceId}</strong>
                                <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                    {count} eventos · fonte {source}
                                </div>
                            </div>
                            <div style={{
                                ...styles.eventBadge,
                                backgroundColor: count > 10 ? '#ef4444' : count > 5 ? '#f59e0b' : '#10b981'
                            }}>
                                {count}
                            </div>
                        </div>
                    );
                })}
            </div>

              </>
            )}
        </div>
    );
};

const getEventColor = (type: string): string => {
    const colors: {[key: string]: string} = {
        'harsh_accel': '#f59e0b',
        'harsh_brake': '#ef4444',
        'speeding': '#dc2626',
        'sharp_turn': '#f97316'
    };
    return colors[type] || '#6b7280';
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        padding: '20px',
        backgroundColor: '#1f2937',
        height: '100%',
        overflowY: 'auto',
        color: 'white',
    },
    title: {
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: '#10b981',
        borderBottom: '2px solid #374151',
        paddingBottom: '10px',
    },
    section: {
        marginBottom: '25px',
        padding: '15px',
        backgroundColor: '#374151',
        borderRadius: '8px',
    },
    sectionTitle: {
        fontSize: '13px',
        fontWeight: 'bold',
        marginBottom: '12px',
        color: '#f3f4f6',
    },
    chartRow: {
        marginBottom: '12px',
    },
    chartLabel: {
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '12px',
        marginBottom: '5px',
        color: '#d1d5db',
    },
    chartValue: {
        fontWeight: 'bold',
        color: '#f3f4f6',
    },
    barContainer: {
        height: '20px',
        backgroundColor: '#1f2937',
        borderRadius: '4px',
        overflow: 'hidden',
    },
    bar: {
        height: '100%',
        transition: 'width 0.3s ease',
    },
    vehicleEventRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px',
        backgroundColor: '#1f2937',
        borderRadius: '6px',
        marginBottom: '8px',
    },
    rank: {
        width: '24px',
        height: '24px',
        borderRadius: '50%',
        backgroundColor: '#4b5563',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: 'bold',
    },
    vehicleEventInfo: {
        flex: 1,
        fontSize: '13px',
    },
    eventBadge: {
        width: '32px',
        height: '32px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: 'bold',
        color: 'white',
    },
    correlationGrid: {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    correlationItem: {
        padding: '10px',
        backgroundColor: '#1f2937',
        borderRadius: '6px',
    },
    correlationDevice: {
        fontSize: '12px',
        fontWeight: 'bold',
        marginBottom: '8px',
        color: '#f3f4f6',
    },
    correlationBars: {
        display: 'flex',
        flexDirection: 'column',
        gap: '5px',
    },
    correlationBarRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    },
    miniBarContainer: {
        flex: 1,
        height: '12px',
        backgroundColor: '#4b5563',
        borderRadius: '3px',
        overflow: 'hidden',
    },
    miniBar: {
        height: '100%',
        transition: 'width 0.3s ease',
    },
};

export default VehicleAnalytics;
