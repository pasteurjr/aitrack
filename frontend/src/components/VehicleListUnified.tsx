import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface UnifiedVehicle {
    id: number;
    placa: string;
    tipo: 'tracker_only' | 'app_only' | 'both';
    descricao: string;
    fonte: string | null;
    posicao_atual: any;
    ultima_viagem: any;
    score: number | null;
    status: string;
}

interface VehicleListUnifiedProps {
    selectedVehicleId: number | null;
    onVehicleSelect: (id: number, placa: string) => void;
}

const VehicleListUnified: React.FC<VehicleListUnifiedProps> = ({
    selectedVehicleId,
    onVehicleSelect
}) => {
    const [vehicles, setVehicles] = useState<UnifiedVehicle[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchVehicles = async () => {
            try {
                const response = await axios.get('http://localhost:5009/api/unified/vehicles');
                if (response.data.success) {
                    setVehicles(response.data.vehicles);
                    setError(null);
                } else {
                    setError('Erro ao carregar veículos');
                }
                setLoading(false);
            } catch (err) {
                setError('Falha ao conectar com o servidor');
                console.error(err);
                setLoading(false);
            }
        };

        fetchVehicles();
        const intervalId = setInterval(fetchVehicles, 5000); // Atualiza a cada 5s

        return () => clearInterval(intervalId);
    }, []);

    const getTipoBadge = (tipo: string) => {
        switch (tipo) {
            case 'tracker_only':
                return <span className="badge bg-primary ms-2">GPS</span>;
            case 'app_only':
                return <span className="badge bg-success ms-2">APP</span>;
            case 'both':
                return <span className="badge bg-warning text-dark ms-2">AMBOS</span>;
            default:
                return null;
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'online':
                return <span className="badge bg-success">Online</span>;
            case 'offline':
                return <span className="badge bg-secondary">Offline</span>;
            default:
                return <span className="badge bg-secondary">?</span>;
        }
    };

    if (loading) {
        return (
            <div className="text-center p-3">
                <div className="spinner-border spinner-border-sm" role="status">
                    <span className="visually-hidden">Carregando...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return <div className="alert alert-danger m-2">{error}</div>;
    }

    if (vehicles.length === 0) {
        return <div className="alert alert-info m-2">Nenhum veículo encontrado</div>;
    }

    return (
        <div>
            <div className="p-2 border-bottom bg-light">
                <small className="text-muted">
                    Total: {vehicles.length} veículos
                </small>
            </div>
            <div className="list-group list-group-flush" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                {vehicles.map(vehicle => (
                    <button
                        type="button"
                        key={vehicle.id}
                        className={`list-group-item list-group-item-action text-start ${
                            selectedVehicleId === vehicle.id ? 'active' : ''
                        }`}
                        onClick={() => onVehicleSelect(vehicle.id, vehicle.placa)}
                    >
                        <div className="d-flex justify-content-between align-items-start">
                            <div className="fw-bold">
                                {vehicle.placa}
                                {getTipoBadge(vehicle.tipo)}
                            </div>
                            {getStatusBadge(vehicle.status)}
                        </div>

                        <small className="text-muted d-block mt-1">
                            {vehicle.descricao}
                        </small>

                        {/* Mostrar score se disponível (dirijabem) */}
                        {vehicle.score !== null && (
                            <div className="mt-2">
                                <small>
                                    Score: <strong>{vehicle.score.toFixed(1)}</strong>/100
                                </small>
                            </div>
                        )}

                        {/* Mostrar velocidade se disponível (tracker) */}
                        {vehicle.posicao_atual && vehicle.posicao_atual.velocidade !== undefined && (
                            <div className="mt-1">
                                <small>
                                    🚗 {vehicle.posicao_atual.velocidade.toFixed(1)} km/h
                                </small>
                            </div>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default VehicleListUnified;
