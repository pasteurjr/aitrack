import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker } from 'react-leaflet';
import { LatLngExpression } from 'leaflet';
import axios from 'axios';
import { movingIcon, stoppedIcon } from '../utils/vehicleIcons';
import MapViewUpdater from './MapViewUpdater';

interface TrailPoint {
    latitude: number;
    longitude: number;
    velocidade_kmh: number;
    DATAHORA: string;
}

interface MapComponentProps {
    selectedVehicleId: number | null;
}

const MapComponent: React.FC<MapComponentProps> = ({ selectedVehicleId }) => {
    const [trail, setTrail] = useState<TrailPoint[]>([]);

    useEffect(() => {
        setTrail([]);

        if (selectedVehicleId === null) return;

        const fetchLatestPosition = async () => {
            try {
                const response = await axios.get<TrailPoint>(`http://localhost:5009/api/positions/latest/${selectedVehicleId}`);
                const latestPoint = response.data;
                if (latestPoint) {
                    setTrail(prevTrail => {
                        // só adiciona se mudou o timestamp
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

        const intervalId = setInterval(fetchLatestPosition, 5000);
        return () => clearInterval(intervalId);

    }, [selectedVehicleId]);

    const lastPoint = trail.length > 0 ? trail[trail.length - 1] : null;

    return (
        <MapContainer center={[-15.79, -47.88]} zoom={4} style={{ height: '100%', width: '100%' }}>
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap contributors' />

            {trail.length > 0 && (
                <>
                    <Polyline positions={trail.map(p => [p.latitude, p.longitude])} color="red" weight={3} />
                    
                    {trail.slice(0, -1).map((point, index) => (
                        <CircleMarker
                            key={index}
                            center={[point.latitude, point.longitude]}
                            radius={3}
                            color="red"
                            fillOpacity={0.8}
                        />
                    ))}

                    {lastPoint && (
                        <Marker 
                            position={[lastPoint.latitude, lastPoint.longitude]} 
                            icon={lastPoint.velocidade_kmh > 0 ? movingIcon : stoppedIcon}
                        >
                            <Popup><b>Velocidade:</b> {lastPoint.velocidade_kmh.toFixed(1)} km/h</Popup>
                        </Marker>
                    )}
                </>
            )}

            <MapViewUpdater points={trail} />
        </MapContainer>
    );
};

export default MapComponent;
