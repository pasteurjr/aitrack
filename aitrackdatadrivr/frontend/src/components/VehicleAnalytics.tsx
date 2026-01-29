import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Event {
    device_id: string;
    type: string;
    severity: string;
}

interface VehicleAnalyticsProps {
    onVehicleClick: (deviceId: string) => void;
}

const VehicleAnalytics: React.FC<VehicleAnalyticsProps> = ({ onVehicleClick }) => {
    const [scores, setScores] = useState<{[key: string]: number}>({});
    const [events, setEvents] = useState<Event[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const scoresResponse = await axios.get('http://localhost:5009/api/fleet/scores');
                setScores(scoresResponse.data);

                const eventsResponse = await axios.get('http://localhost:5009/api/fleet/events?limit=100');
                setEvents(eventsResponse.data);
            } catch (error) {
                console.error("Erro ao buscar dados:", error);
            }
        };

        fetchData();
        const intervalId = setInterval(fetchData, 5000);
        return () => clearInterval(intervalId);
    }, []);

    // Calcular distribuição de eventos por tipo
    const eventsByType = events.reduce((acc, event) => {
        acc[event.type] = (acc[event.type] || 0) + 1;
        return acc;
    }, {} as {[key: string]: number});

    // Calcular distribuição de eventos por veículo
    const eventsByVehicle = events.reduce((acc, event) => {
        acc[event.device_id] = (acc[event.device_id] || 0) + 1;
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

            {/* Distribuição de Eventos por Tipo */}
            <div style={styles.section}>
                <h4 style={styles.sectionTitle}>Eventos por Tipo</h4>
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
                {topVehiclesByEvents.map(([device_id, count], index) => {
                    const score = scores[device_id] || 0;
                    return (
                        <div
                            key={device_id}
                            style={{...styles.vehicleEventRow, cursor: 'pointer'}}
                            onClick={() => onVehicleClick(device_id)}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4b5563'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#1f2937'}
                        >
                            <div style={styles.rank}>{index + 1}</div>
                            <div style={styles.vehicleEventInfo}>
                                <strong>{device_id}</strong>
                                <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                    {count} eventos • Score: {score.toFixed(1)}
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

            {/* Correlação Score x Eventos */}
            <div style={styles.section}>
                <h4 style={styles.sectionTitle}>📊 Correlação Score x Eventos</h4>
                <div style={styles.correlationGrid}>
                    {Object.entries(scores)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 10)
                        .map(([device_id, score]) => {
                            const eventCount = eventsByVehicle[device_id] || 0;
                            return (
                                <div key={device_id} style={styles.correlationItem}>
                                    <div style={styles.correlationDevice}>{device_id}</div>
                                    <div style={styles.correlationBars}>
                                        <div style={styles.correlationBarRow}>
                                            <span style={{ fontSize: '10px', width: '50px' }}>Score:</span>
                                            <div style={styles.miniBarContainer}>
                                                <div style={{
                                                    ...styles.miniBar,
                                                    width: `${score}%`,
                                                    backgroundColor: getScoreColor(score)
                                                }} />
                                            </div>
                                            <span style={{ fontSize: '10px', width: '30px' }}>{score.toFixed(0)}</span>
                                        </div>
                                        <div style={styles.correlationBarRow}>
                                            <span style={{ fontSize: '10px', width: '50px' }}>Eventos:</span>
                                            <div style={styles.miniBarContainer}>
                                                <div style={{
                                                    ...styles.miniBar,
                                                    width: `${Math.min(eventCount * 5, 100)}%`,
                                                    backgroundColor: '#ef4444'
                                                }} />
                                            </div>
                                            <span style={{ fontSize: '10px', width: '30px' }}>{eventCount}</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                </div>
            </div>

            {totalEvents === 0 && (
                <div style={styles.emptyState}>
                    Aguardando dados de eventos...
                </div>
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

const getScoreColor = (score: number): string => {
    if (score >= 75) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
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
    emptyState: {
        textAlign: 'center',
        padding: '40px 20px',
        color: '#6b7280',
        fontSize: '14px',
    },
};

export default VehicleAnalytics;
