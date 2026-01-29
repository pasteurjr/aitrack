import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Event {
    device_id: string;
    type: string;
    timestamp: string;
    severity: string;
    icon: string;
    lat: number;
    lon: number;
}

interface EventsTimelineProps {
    onEventClick: (eventIndex: number) => void;
}

const EventsTimeline: React.FC<EventsTimelineProps> = ({ onEventClick }) => {
    const [events, setEvents] = useState<Event[]>([]);

    useEffect(() => {
        const fetchEvents = async () => {
            try {
                const response = await axios.get('http://localhost:5009/api/fleet/events?limit=50');
                setEvents(response.data);
            } catch (error) {
                console.error("Erro ao buscar eventos:", error);
            }
        };

        fetchEvents();
        const intervalId = setInterval(fetchEvents, 5000);
        return () => clearInterval(intervalId);
    }, []);

    const eventLabels: {[key: string]: string} = {
        'harsh_accel': 'Aceleração Brusca',
        'harsh_brake': 'Frenagem Brusca',
        'speeding': 'Excesso de Velocidade',
        'sharp_turn': 'Curva Brusca'
    };

    const getSeverityColor = (severity: string) => {
        if (severity === 'high') return '#ef4444';
        if (severity === 'medium') return '#f59e0b';
        return '#10b981';
    };

    return (
        <div style={styles.container}>
            <h3 style={styles.title}>⏱️ TIMELINE DE EVENTOS</h3>

            <div style={styles.timeline}>
                {events.map((event, index) => (
                    <div
                        key={index}
                        style={{...styles.eventRow, cursor: 'pointer'}}
                        onClick={() => onEventClick(index)}
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
                                    {event.severity === 'high' ? 'Alta' :
                                     event.severity === 'medium' ? 'Média' : 'Baixa'}
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {events.length === 0 && (
                <div style={styles.emptyState}>
                    Aguardando eventos...
                </div>
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
    timeline: {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    eventRow: {
        display: 'flex',
        gap: '12px',
        alignItems: 'flex-start',
        padding: '12px',
        backgroundColor: '#374151',
        borderRadius: '6px',
        borderLeft: '3px solid #10b981',
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
    emptyState: {
        textAlign: 'center',
        padding: '40px 20px',
        color: '#6b7280',
        fontSize: '14px',
    },
};

export default EventsTimeline;
