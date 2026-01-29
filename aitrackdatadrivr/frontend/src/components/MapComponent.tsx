import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, useMap } from 'react-leaflet';
import { divIcon } from 'leaflet';
import axios from 'axios';
import MapViewUpdater from './MapViewUpdater';
import L from 'leaflet';

// Controlador para seguir a rota Dirijabem automaticamente
const DirijabemMapViewUpdater: React.FC<{
    route: Array<{lat: number, lon: number}>
}> = ({ route }) => {
    const map = useMap();

    useEffect(() => {
        if (!route || route.length === 0) return;

        // Create bounds from all points in the route
        const bounds = L.latLngBounds(route.map(p => [p.lat, p.lon]));

        // Fit map to show all points with padding
        map.fitBounds(bounds, { padding: [50, 50] });

    }, [route, map]);

    return null;
};

// Controlador para centralizar no evento destacado
const EventMapController: React.FC<{
    events: BehavioralEvent[],
    highlightedIndex: number | null,
    filterByVehicle: string | null,
    vehicles: Vehicle[]
}> = ({ events, highlightedIndex, filterByVehicle, vehicles }) => {
    const map = useMap();
    const [lastHighlightedIndex, setLastHighlightedIndex] = React.useState<number | null>(null);
    const [lastFilteredVehicle, setLastFilteredVehicle] = React.useState<string | null>(null);

    // Centralizar quando destaca um evento - APENAS UMA VEZ
    useEffect(() => {
        if (highlightedIndex !== null && highlightedIndex !== undefined && events.length > 0) {
            // Só centraliza se mudou o evento
            if (highlightedIndex !== lastHighlightedIndex) {
                const event = events[highlightedIndex];
                console.log('🎯 Centralizando ESTATICAMENTE no evento:', event);
                if (event) {
                    setTimeout(() => {
                        map.setView([event.lat, event.lon], 17, { animate: true });
                        setLastHighlightedIndex(highlightedIndex);
                    }, 100);
                }
            }
        } else if (highlightedIndex === null) {
            setLastHighlightedIndex(null);
        }
    }, [highlightedIndex, events, map, lastHighlightedIndex]);

    // Centralizar quando filtra por veículo - APENAS UMA VEZ
    useEffect(() => {
        if (filterByVehicle && vehicles.length > 0) {
            // Só centraliza se mudou o veículo
            if (filterByVehicle !== lastFilteredVehicle) {
                const vehicle = vehicles.find(v => v.device_id === filterByVehicle);
                console.log('🎯 Centralizando no veículo filtrado:', vehicle);
                if (vehicle) {
                    setTimeout(() => {
                        map.setView([vehicle.lat, vehicle.lon], 14, { animate: true });
                        setLastFilteredVehicle(filterByVehicle);
                    }, 100);
                }
            }
        } else if (!filterByVehicle) {
            setLastFilteredVehicle(null);
        }
    }, [filterByVehicle, vehicles, map, lastFilteredVehicle]);

    return null;
};

interface TrailPoint {
    latitude: number;
    longitude: number;
    velocidade_kmh: number;
    DATAHORA: string;
}

interface Vehicle {
    device_id: string;
    veicod: number;
    lat: number;
    lon: number;
    speed: number;
    score: number;
}

interface BehavioralEvent {
    device_id: string;
    type: string;
    lat: number;
    lon: number;
    timestamp: string;
    severity: string;
    icon: string;
}

interface MapComponentProps {
    selectedVehicleId?: string | null;
    selectedUserId?: number | null;
    highlightedEventIndex?: number | null;
    filterEventsByVehicle?: string | null;
    onClearEventHighlight?: () => void;
    onClearFilter?: () => void;
}

const MapComponent: React.FC<MapComponentProps> = ({
    selectedVehicleId,
    selectedUserId,
    highlightedEventIndex,
    filterEventsByVehicle,
    onClearEventHighlight,
    onClearFilter
}) => {
    const [vehicles, setVehicles] = useState<Vehicle[]>([]);
    const [events, setEvents] = useState<BehavioralEvent[]>([]);
    const [trail, setTrail] = useState<TrailPoint[]>([]);
    const [selectedVeicod, setSelectedVeicod] = useState<number | null>(null);
    const [dirijabemRoute, setDirijabemRoute] = useState<Array<{lat: number, lon: number, timestamp: string, speed: number}>>([]);
    const [lastSelectedUserId, setLastSelectedUserId] = useState<number | null>(null);

    // Debug logs
    React.useEffect(() => {
        console.log('MapComponent recebeu:', {
            selectedVehicleId,
            highlightedEventIndex,
            filterEventsByVehicle,
            eventsCount: events.length
        });
    }, [selectedVehicleId, highlightedEventIndex, filterEventsByVehicle, events.length]);

    // Quando destaca evento, busca TODOS os eventos UMA VEZ e mantém
    React.useEffect(() => {
        if (highlightedEventIndex !== null && highlightedEventIndex !== undefined && events.length === 0) {
            console.log('🔍 Buscando eventos para modo timeline...');
            const fetchEvents = async () => {
                try {
                    const eventsResponse = await axios.get('http://localhost:5009/api/fleet/events?limit=50');
                    setEvents(eventsResponse.data);
                    console.log('✅ Eventos carregados:', eventsResponse.data.length);
                } catch (error) {
                    console.error("Erro ao buscar eventos:", error);
                }
            };
            fetchEvents();
        }
    }, [highlightedEventIndex, events.length]);

    const getMarkerColor = (score: number): string => {
        if (score >= 75) return '#10b981';
        if (score >= 50) return '#f59e0b';
        return '#ef4444';
    };

    const getVehicleIcon = (score: number, isSelected: boolean = false) => {
        const color = getMarkerColor(score);
        const borderColor = isSelected ? '#10b981' : 'white';
        const borderWidth = isSelected ? '4px' : '3px';
        const size = isSelected ? 50 : 40;

        return divIcon({
            html: `
                <div style="
                    background: ${color};
                    border-radius: 50%;
                    width: ${size}px;
                    height: ${size}px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: ${isSelected ? 18 : 14}px;
                    border: ${borderWidth} solid ${borderColor};
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                ">
                    ${Math.round(score)}
                </div>
            `,
            iconSize: [size, size],
            className: 'vehicle-marker'
        });
    };

    const getEventIcon = (event: BehavioralEvent, isHighlighted: boolean = false) => {
        const colors: {[key: string]: string} = {
            'harsh_accel': '#f59e0b',
            'harsh_brake': '#ef4444',
            'speeding': '#dc2626',
            'sharp_turn': '#f97316'
        };

        const size = isHighlighted ? 45 : 30;
        const borderWidth = isHighlighted ? '4px' : '2px';
        const borderColor = isHighlighted ? '#10b981' : 'white';

        return divIcon({
            html: `
                <div style="
                    font-size: ${isHighlighted ? 28 : 20}px;
                    background: ${colors[event.type] || '#666'};
                    border-radius: 50%;
                    width: ${size}px;
                    height: ${size}px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: ${borderWidth} solid ${borderColor};
                    box-shadow: 0 ${isHighlighted ? 4 : 2}px ${isHighlighted ? 8 : 4}px rgba(0,0,0,${isHighlighted ? 0.5 : 0.3});
                    ${isHighlighted ? 'animation: pulse 1.5s infinite;' : ''}
                ">
                    ${event.icon}
                </div>
                ${isHighlighted ? `<style>
                    @keyframes pulse {
                        0%, 100% { transform: scale(1); }
                        50% { transform: scale(1.1); }
                    }
                </style>` : ''}
            `,
            iconSize: [size, size],
            className: 'event-marker'
        });
    };

    // Buscar veículos e eventos - MAS NÃO atualiza se tem evento destacado
    useEffect(() => {
        const fetchData = async () => {
            try {
                const scoresResponse = await axios.get('http://localhost:5009/api/fleet/scores');
                const scores = scoresResponse.data;

                // Buscar veículos do banco
                const positionsResponse = await axios.get('http://localhost:5009/api/posicoes');
                const vehiclesFromDB = positionsResponse.data;

                const vehiclesWithScores: Vehicle[] = vehiclesFromDB.map((v: any) => ({
                    device_id: v.VEI_DEVICE_ID || `VEI-${v.VEICOD}`,
                    veicod: v.VEICOD,
                    lat: v.latitude || -23.55,
                    lon: v.longitude || -46.63,
                    speed: v.velocidade_kmh || 0,
                    score: scores[v.VEI_DEVICE_ID] || 85
                }));

                setVehicles(vehiclesWithScores);

                // IMPORTANTE: Só busca novos eventos se NÃO tem evento destacado
                if (highlightedEventIndex === null || highlightedEventIndex === undefined) {
                    const eventsResponse = await axios.get('http://localhost:5009/api/fleet/events?limit=20');
                    setEvents(eventsResponse.data);
                }

            } catch (error) {
                console.error("Erro ao buscar dados:", error);
            }
        };

        fetchData();
        // Só atualiza automaticamente se NÃO tem evento destacado
        if (highlightedEventIndex === null || highlightedEventIndex === undefined) {
            const intervalId = setInterval(fetchData, 3000);
            return () => clearInterval(intervalId);
        }
    }, [highlightedEventIndex]);

    // Quando seleciona veículo, mapear device_id -> veicod
    useEffect(() => {
        if (selectedVehicleId) {
            const vehicle = vehicles.find(v => v.device_id === selectedVehicleId);
            if (vehicle) {
                setSelectedVeicod(vehicle.veicod);
            }
        } else {
            setSelectedVeicod(null);
        }
    }, [selectedVehicleId, vehicles]);

    // Buscar trilha em tempo real (IGUAL AO ORIGINAL)
    useEffect(() => {
        setTrail([]);

        if (selectedVeicod === null) return;

        const fetchLatestPosition = async () => {
            try {
                const response = await axios.get<TrailPoint>(`http://localhost:5009/api/positions/latest/${selectedVeicod}`);
                const latestPoint = response.data;
                if (latestPoint) {
                    setTrail(prevTrail => {
                        // Só adiciona se mudou o timestamp
                        if (prevTrail.length === 0 || prevTrail[prevTrail.length - 1].DATAHORA !== latestPoint.DATAHORA) {
                            return [...prevTrail, latestPoint];
                        }
                        return prevTrail;
                    });
                }
            } catch (error) {
                console.error("Erro ao buscar última posição:", error);
            }
        };

        fetchLatestPosition();
        const intervalId = setInterval(fetchLatestPosition, 5000);
        return () => clearInterval(intervalId);

    }, [selectedVeicod]);

    // Fetch DIRIJABEM route - ALWAYS fetch full route when user changes
    useEffect(() => {
        console.log('[MAP-DIRIJABEM] selectedUserId changed:', selectedUserId);

        // Case 1: No user selected - clear everything
        if (selectedUserId === null || selectedUserId === undefined) {
            console.log('[MAP-DIRIJABEM] No user selected, clearing route');
            setDirijabemRoute([]);
            setLastSelectedUserId(null);
            return;
        }

        // Case 2: Different user selected - fetch full route from backend
        console.log('[MAP-DIRIJABEM] Loading user', selectedUserId, '- fetching full route from backend');
        setDirijabemRoute([]);  // Clear previous route
        setLastSelectedUserId(selectedUserId);

        // Fetch full route from backend (includes all existing points)
        const fetchFullRoute = async () => {
            try {
                console.log('[MAP-DIRIJABEM] 📡 Calling /route endpoint for user:', selectedUserId);
                const response = await axios.get<Array<{lat: number, lon: number, timestamp: string, speed: number}>>(
                    `http://localhost:5009/api/dirijabem/user/${selectedUserId}/route`
                );
                const points = response.data;

                console.log('[MAP-DIRIJABEM] 📥 Backend returned', points ? points.length : 0, 'points');

                if (points && points.length > 0) {
                    console.log('[MAP-DIRIJABEM] ✅ Setting route with', points.length, 'existing points');
                    console.log('[MAP-DIRIJABEM] First point:', points[0].lat, points[0].lon);
                    console.log('[MAP-DIRIJABEM] Last point:', points[points.length - 1].lat, points[points.length - 1].lon);
                    setDirijabemRoute(points);
                } else {
                    console.log('[MAP-DIRIJABEM] ⚠️ No existing points, route will build as trip progresses');
                }
            } catch (error) {
                console.error("[MAP-DIRIJABEM] ❌ Error fetching full route:", error);
            }
        };

        // Fetch full route first
        fetchFullRoute();

        // Define fetchLastPoint for incremental polling
        const fetchLastPoint = async () => {
            try {
                const response = await axios.get<{lat: number, lon: number, timestamp: string, speed: number} | null>(
                    `http://localhost:5009/api/dirijabem/user/${selectedUserId}/last-point`
                );
                const latestPoint = response.data;

                if (latestPoint) {
                    setDirijabemRoute(prevRoute => {
                        // Only add if timestamp changed
                        if (prevRoute.length === 0 ||
                            prevRoute[prevRoute.length - 1].timestamp !== latestPoint.timestamp) {
                            console.log('[MAP-DIRIJABEM] New point, total:', prevRoute.length + 1);
                            return [...prevRoute, latestPoint];
                        }
                        return prevRoute;
                    });
                }
            } catch (error) {
                console.error("[MAP-DIRIJABEM] Error fetching last point:", error);
            }
        };

        // Start incremental polling after a brief delay (let full route load first)
        let intervalId: NodeJS.Timeout | null = null;

        const timeoutId = setTimeout(() => {
            fetchLastPoint(); // Execute first poll
            intervalId = setInterval(fetchLastPoint, 5000);
        }, 2000); // Wait 2 seconds for full route to load

        return () => {
            clearTimeout(timeoutId);
            if (intervalId) clearInterval(intervalId);
        };

    }, [selectedUserId]);

    const lastPoint = trail.length > 0 ? trail[trail.length - 1] : null;
    const lastDirijabemPoint = dirijabemRoute.length > 0 ? dirijabemRoute[dirijabemRoute.length - 1] : null;

    const eventLabels: {[key: string]: string} = {
        'harsh_accel': 'Aceleração Brusca',
        'harsh_brake': 'Frenagem Brusca',
        'speeding': 'Excesso de Velocidade',
        'sharp_turn': 'Curva Brusca'
    };

    // Calcular quantos eventos estão sendo exibidos
    const displayedEventsCount = filterEventsByVehicle
        ? events.filter(e => e.device_id === filterEventsByVehicle).length
        : events.length;

    // Debug: contar eventos visíveis
    React.useEffect(() => {
        if (highlightedEventIndex !== null && highlightedEventIndex !== undefined) {
            console.log('👁️ Modo Timeline ativo:', {
                highlightedEventIndex,
                totalEvents: events.length,
                eventoDestacado: events[highlightedEventIndex]
            });
        }
    }, [highlightedEventIndex, events]);

    return (
        <div style={{ position: 'relative', height: '100%', width: '100%' }}>
            {/* Banner - Evento único destacado */}
            {highlightedEventIndex !== null && highlightedEventIndex !== undefined && events[highlightedEventIndex] && (
                <div style={{
                    position: 'absolute',
                    top: '10px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 1000,
                    backgroundColor: '#ef4444',
                    color: 'white',
                    padding: '10px 20px',
                    borderRadius: '8px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '14px',
                    fontWeight: 'bold'
                }}>
                    <span>{events[highlightedEventIndex].icon} Visualizando evento específico</span>
                    <span style={{
                        backgroundColor: 'white',
                        color: '#ef4444',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px'
                    }}>
                        {events[highlightedEventIndex].device_id}
                    </span>
                    <button
                        onClick={onClearEventHighlight}
                        style={{
                            backgroundColor: 'white',
                            color: '#ef4444',
                            border: 'none',
                            borderRadius: '50%',
                            width: '24px',
                            height: '24px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '16px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                        title="Limpar seleção"
                    >
                        ×
                    </button>
                </div>
            )}

            {/* Filtro ativo - Banner informativo - NÃO mostra se tem evento destacado */}
            {filterEventsByVehicle && !highlightedEventIndex && (
                <div style={{
                    position: 'absolute',
                    top: '10px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 1000,
                    backgroundColor: '#10b981',
                    color: 'white',
                    padding: '10px 20px',
                    borderRadius: '8px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '14px',
                    fontWeight: 'bold'
                }}>
                    <span>🔍 Filtrando eventos de {filterEventsByVehicle}</span>
                    <span style={{
                        backgroundColor: 'white',
                        color: '#10b981',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px'
                    }}>
                        {displayedEventsCount} eventos
                    </span>
                    <button
                        onClick={onClearFilter}
                        style={{
                            backgroundColor: 'white',
                            color: '#10b981',
                            border: 'none',
                            borderRadius: '50%',
                            width: '24px',
                            height: '24px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '16px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                        title="Limpar filtro"
                    >
                        ×
                    </button>
                </div>
            )}

            <MapContainer center={[-23.55, -46.63]} zoom={13} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; OpenStreetMap contributors'
                />

                {/* MapViewUpdater DESABILITADO quando tem evento destacado */}
                {!highlightedEventIndex && <MapViewUpdater points={trail} />}

                <EventMapController
                    events={events}
                    highlightedIndex={highlightedEventIndex || null}
                    filterByVehicle={filterEventsByVehicle || null}
                    vehicles={vehicles}
                />

                {dirijabemRoute.length > 0 && !highlightedEventIndex && (
                    <DirijabemMapViewUpdater route={dirijabemRoute} />
                )}

            {/* Marcadores de Veículos (se NÃO tem selecionado E NÃO tem filtro E NÃO tem evento destacado) */}
            {!selectedVehicleId && !filterEventsByVehicle && !highlightedEventIndex && vehicles.map((vehicle) => (
                <Marker
                    key={vehicle.device_id}
                    position={[vehicle.lat, vehicle.lon]}
                    icon={getVehicleIcon(vehicle.score, false)}
                >
                    <Popup>
                        <div style={{ minWidth: '200px' }}>
                            <h3 style={{
                                margin: '0 0 10px 0',
                                color: getMarkerColor(vehicle.score),
                                fontSize: '16px'
                            }}>
                                {vehicle.device_id}
                            </h3>
                            <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                                <strong>Score:</strong> {Math.round(vehicle.score)}/100<br/>
                                <strong>Status:</strong> {
                                    vehicle.score >= 75 ? '🟢 Seguro' :
                                    vehicle.score >= 50 ? '🟡 Atenção' :
                                    '🔴 Alto Risco'
                                }<br/>
                                <strong>Velocidade:</strong> {vehicle.speed.toFixed(1)} km/h
                            </div>
                        </div>
                    </Popup>
                </Marker>
            ))}

            {/* Marcadores de Eventos */}
            {events.map((event, index) => {
                // MODO: Evento único destacado (Timeline) - mostra APENAS esse evento
                if (highlightedEventIndex !== null && highlightedEventIndex !== undefined) {
                    if (index !== highlightedEventIndex) {
                        return null; // Não mostra outros eventos
                    }
                    console.log('🎯 Renderizando evento destacado:', {
                        index,
                        event,
                        lat: event.lat,
                        lon: event.lon,
                        type: event.type
                    });
                }

                // Se tem veículo selecionado E NÃO tem filtro, não mostra eventos (mostra trilha)
                if (selectedVehicleId && !filterEventsByVehicle && !highlightedEventIndex) {
                    return null;
                }

                // Filtrar eventos se filterEventsByVehicle está ativo
                if (filterEventsByVehicle && event.device_id !== filterEventsByVehicle) {
                    return null;
                }

                const eventVehicle = vehicles.find(v => v.device_id === event.device_id);
                const isHighlighted = highlightedEventIndex === index;

                return (
                    <Marker
                        key={`event-${index}`}
                        position={[event.lat, event.lon]}
                        icon={getEventIcon(event, isHighlighted)}
                    >
                        <Popup>
                            <div style={{
                                minWidth: '280px',
                                ...(isHighlighted && {
                                    border: '3px solid #10b981',
                                    borderRadius: '8px',
                                    padding: '10px',
                                    backgroundColor: '#ecfdf5'
                                })
                            }}>
                                {isHighlighted && (
                                    <div style={{
                                        backgroundColor: '#10b981',
                                        color: 'white',
                                        padding: '5px 10px',
                                        borderRadius: '4px',
                                        marginBottom: '10px',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        textAlign: 'center'
                                    }}>
                                        ⭐ EVENTO SELECIONADO NA TIMELINE
                                    </div>
                                )}
                                <h3 style={{
                                    margin: '0 0 10px 0',
                                    fontSize: '16px',
                                    borderBottom: '2px solid #ef4444',
                                    paddingBottom: '5px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}>
                                    <span style={{ fontSize: '24px' }}>{event.icon}</span>
                                    <span>{eventLabels[event.type] || event.type}</span>
                                </h3>

                                <div style={{ fontSize: '13px', lineHeight: '1.8', marginBottom: '10px' }}>
                                    <strong>🚗 Veículo:</strong> {event.device_id}<br/>
                                    <strong>🕒 Horário:</strong> {new Date(event.timestamp).toLocaleString()}<br/>
                                    <strong>⚠️ Severidade:</strong> {
                                        event.severity === 'high' ? '🔴 Alta' :
                                        event.severity === 'medium' ? '🟡 Média' :
                                        '🟢 Baixa'
                                    }
                                </div>

                                {/* Detalhes específicos do evento */}
                                <div style={{
                                    backgroundColor: '#fef3c7',
                                    padding: '10px',
                                    borderRadius: '4px',
                                    marginBottom: '10px',
                                    fontSize: '12px'
                                }}>
                                    <strong>📈 Detalhes Técnicos:</strong><br/>
                                    {event.type === 'harsh_accel' && (event as any).acceleration_ms2 && (
                                        <>
                                            Aceleração: {(event as any).acceleration_ms2} m/s²<br/>
                                            Delta velocidade: {(event as any).delta?.toFixed(1)} km/h
                                        </>
                                    )}
                                    {event.type === 'harsh_brake' && (event as any).deceleration_ms2 && (
                                        <>
                                            Desaceleração: {(event as any).deceleration_ms2} m/s²<br/>
                                            Delta velocidade: {(event as any).delta?.toFixed(1)} km/h
                                        </>
                                    )}
                                    {event.type === 'speeding' && (event as any).excess && (
                                        <>
                                            Velocidade: {(event as any).speed?.toFixed(1)} km/h<br/>
                                            Limite: {(event as any).speed_limit} km/h<br/>
                                            Excesso: +{(event as any).excess.toFixed(1)} km/h
                                        </>
                                    )}
                                    {event.type === 'sharp_turn' && (event as any).heading_change && (
                                        <>
                                            Mudança de direção: {(event as any).heading_change.toFixed(0)}°<br/>
                                            Velocidade na curva: {(event as any).speed?.toFixed(1)} km/h
                                        </>
                                    )}
                                </div>

                                {eventVehicle && (
                                    <div style={{
                                        backgroundColor: '#f3f4f6',
                                        padding: '8px',
                                        borderRadius: '4px',
                                        fontSize: '12px'
                                    }}>
                                        <strong>📊 Score Atual do Veículo:</strong>
                                        <div style={{
                                            fontSize: '20px',
                                            fontWeight: 'bold',
                                            color: getMarkerColor(eventVehicle.score),
                                            textAlign: 'center',
                                            margin: '5px 0'
                                        }}>
                                            {Math.round(eventVehicle.score)}/100
                                        </div>
                                    </div>
                                )}

                                <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '8px', fontStyle: 'italic' }}>
                                    📍 {event.lat.toFixed(5)}, {event.lon.toFixed(5)}
                                </div>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}

            {/* TRILHA EM TEMPO REAL (IGUAL AO ORIGINAL) - só mostra se NÃO tem evento destacado */}
            {trail.length > 0 && !highlightedEventIndex && (
                <>
                    <Polyline
                        positions={trail.map(p => [p.latitude, p.longitude])}
                        color="red"
                        weight={3}
                    />

                    {trail.slice(0, -1).map((point, index) => {
                        const currentVehicle = vehicles.find(v => v.veicod === selectedVeicod);
                        const eventsAtPoint = events.filter(e =>
                            Math.abs(e.lat - point.latitude) < 0.001 &&
                            Math.abs(e.lon - point.longitude) < 0.001
                        );

                        return (
                            <CircleMarker
                                key={index}
                                center={[point.latitude, point.longitude]}
                                radius={eventsAtPoint.length > 0 ? 5 : 3}
                                color={eventsAtPoint.length > 0 ? '#ef4444' : '#dc2626'}
                                fillColor={eventsAtPoint.length > 0 ? '#fca5a5' : '#ef4444'}
                                fillOpacity={eventsAtPoint.length > 0 ? 0.9 : 0.6}
                            >
                                <Popup>
                                    <div style={{ minWidth: '250px' }}>
                                        <h4 style={{ margin: '0 0 10px 0', borderBottom: '2px solid #ef4444', paddingBottom: '5px' }}>
                                            📍 Ponto da Trilha #{index + 1}
                                        </h4>

                                        <div style={{ fontSize: '13px', lineHeight: '1.6', marginBottom: '10px' }}>
                                            <strong>🕒 Horário:</strong> {new Date(point.DATAHORA).toLocaleString()}<br/>
                                            <strong>🚗 Velocidade:</strong> {point.velocidade_kmh.toFixed(1)} km/h
                                        </div>

                                        {currentVehicle && (
                                            <div style={{
                                                backgroundColor: '#f3f4f6',
                                                padding: '8px',
                                                borderRadius: '4px',
                                                marginBottom: '10px'
                                            }}>
                                                <strong>📊 Score Comportamental:</strong>
                                                <div style={{
                                                    fontSize: '24px',
                                                    fontWeight: 'bold',
                                                    color: getMarkerColor(currentVehicle.score),
                                                    textAlign: 'center',
                                                    margin: '5px 0'
                                                }}>
                                                    {Math.round(currentVehicle.score)}/100
                                                </div>
                                                <div style={{ fontSize: '11px', textAlign: 'center' }}>
                                                    {currentVehicle.score >= 75 ? '🟢 Seguro' :
                                                     currentVehicle.score >= 50 ? '🟡 Atenção' : '🔴 Alto Risco'}
                                                </div>
                                            </div>
                                        )}

                                        {eventsAtPoint.length > 0 && (
                                            <div style={{
                                                backgroundColor: '#fee2e2',
                                                padding: '8px',
                                                borderRadius: '4px',
                                                border: '1px solid #ef4444'
                                            }}>
                                                <strong>⚠️ Eventos Detectados ({eventsAtPoint.length}):</strong>
                                                {eventsAtPoint.map((evt, i) => (
                                                    <div key={i} style={{
                                                        marginTop: '5px',
                                                        fontSize: '12px',
                                                        paddingLeft: '10px',
                                                        borderLeft: '3px solid #ef4444'
                                                    }}>
                                                        <strong>{evt.icon} {eventLabels[evt.type]}</strong><br/>
                                                        Severidade: {evt.severity === 'high' ? '🔴 Alta' :
                                                                    evt.severity === 'medium' ? '🟡 Média' : '🟢 Baixa'}
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '8px', fontStyle: 'italic' }}>
                                            📍 Lat: {point.latitude.toFixed(5)}, Lon: {point.longitude.toFixed(5)}
                                        </div>
                                    </div>
                                </Popup>
                            </CircleMarker>
                        );
                    })}

                    {lastPoint && (
                        <Marker
                            position={[lastPoint.latitude, lastPoint.longitude]}
                            icon={getVehicleIcon(vehicles.find(v => v.veicod === selectedVeicod)?.score || 85, true)}
                        >
                            <Popup>
                                <div>
                                    <strong>Velocidade:</strong> {lastPoint.velocidade_kmh.toFixed(1)} km/h<br/>
                                    <strong>Horário:</strong> {new Date(lastPoint.DATAHORA).toLocaleString()}
                                </div>
                            </Popup>
                        </Marker>
                    )}
                </>
            )}

            {/* DIRIJABEM ROUTE (GREEN) - só mostra se NÃO tem evento destacado */}
            {dirijabemRoute.length > 0 && !highlightedEventIndex && (
                <>
                    <Polyline
                        positions={dirijabemRoute.map(p => [p.lat, p.lon])}
                        color="#10b981"
                        weight={3}
                    />

                    {dirijabemRoute.slice(0, -1).map((point, index) => (
                        <CircleMarker
                            key={`dirijabem-${index}`}
                            center={[point.lat, point.lon]}
                            radius={3}
                            color="#10b981"
                            fillColor="#34d399"
                            fillOpacity={0.6}
                        >
                            <Popup>
                                <div style={{ minWidth: '250px' }}>
                                    <h4 style={{ margin: '0 0 10px 0', borderBottom: '2px solid #10b981', paddingBottom: '5px' }}>
                                        🏁 Ponto Dirijabem #{index + 1}
                                    </h4>

                                    <div style={{ fontSize: '13px', lineHeight: '1.6', marginBottom: '10px' }}>
                                        <strong>🕒 Horário:</strong> {new Date(point.timestamp).toLocaleString()}<br/>
                                        <strong>🚗 Velocidade:</strong> {point.speed.toFixed(1)} km/h
                                    </div>

                                    <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '8px', fontStyle: 'italic' }}>
                                        📍 Lat: {point.lat.toFixed(5)}, Lon: {point.lon.toFixed(5)}
                                    </div>
                                </div>
                            </Popup>
                        </CircleMarker>
                    ))}

                    {lastDirijabemPoint && (
                        <Marker
                            position={[lastDirijabemPoint.lat, lastDirijabemPoint.lon]}
                            icon={divIcon({
                                html: `
                                    <div style="
                                        background: #10b981;
                                        border-radius: 50%;
                                        width: 50px;
                                        height: 50px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        color: white;
                                        font-weight: bold;
                                        font-size: 18px;
                                        border: 4px solid white;
                                        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                                    ">
                                        🏁
                                    </div>
                                `,
                                iconSize: [50, 50],
                                className: 'dirijabem-marker'
                            })}
                        >
                            <Popup>
                                <div>
                                    <strong>🏁 Posição Atual Dirijabem</strong><br/>
                                    <strong>Velocidade:</strong> {lastDirijabemPoint.speed.toFixed(1)} km/h<br/>
                                    <strong>Horário:</strong> {new Date(lastDirijabemPoint.timestamp).toLocaleString()}
                                </div>
                            </Popup>
                        </Marker>
                    )}
                </>
            )}
            </MapContainer>
        </div>
    );
};

export default MapComponent;
