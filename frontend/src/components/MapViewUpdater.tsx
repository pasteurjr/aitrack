import { useMap } from 'react-leaflet';
import { useEffect } from 'react';
import L from 'leaflet';

const MapViewUpdater = ({ points }: { points: any[] }) => {
    const map = useMap();

    useEffect(() => {
        if (!points || points.length === 0) return;

        // Cria um grupo de coordenadas com todos os pontos do rastro
        const bounds = L.latLngBounds(points.map(p => [p.latitude, p.longitude]));

        // Ajusta o mapa para mostrar todos os pontos, com um pouco de preenchimento
        map.fitBounds(bounds, { padding: [50, 50] });
        
    }, [points, map]);

    return null;
};

export default MapViewUpdater;