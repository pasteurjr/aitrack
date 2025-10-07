import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Vehicle {
    VEICOD: number;
    VEIPLACA: string;
}

interface VehicleListProps {
    selectedVehicleId: number | null;
    onVehicleSelect: (id: number) => void;
}

const VehicleList: React.FC<VehicleListProps> = ({ selectedVehicleId, onVehicleSelect }) => {
    const [vehicles, setVehicles] = useState<Vehicle[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchVehicles = async () => {
            try {
                const response = await axios.get<Vehicle[]>('http://localhost:5009/api/posicoes');
                const uniqueVehicles = Array.from(new Map(response.data.map(v => [v.VEICOD, v])).values());
                setVehicles(uniqueVehicles);
            } catch (err) {
                setError('Falha ao carregar veículos.');
                console.error(err);
            }
        };

        fetchVehicles();
        const intervalId = setInterval(fetchVehicles, 5000);

        return () => clearInterval(intervalId);
    }, []);

    if (error) {
        return <div className="alert alert-danger m-2">{error}</div>;
    }

    return (
        <div className="list-group list-group-flush">
            {vehicles.map(vehicle => (
                <button 
                    type="button"
                    key={vehicle.VEICOD} 
                    className={`list-group-item list-group-item-action text-start ${selectedVehicleId === vehicle.VEICOD ? 'active' : ''}`}
                    onClick={() => onVehicleSelect(vehicle.VEICOD)}
                >
                    <div className="fw-bold">Placa: {vehicle.VEIPLACA}</div>
                    <small>ID: {vehicle.VEICOD}</small>
                </button>
            ))}
        </div>
    );
};

export default VehicleList;
