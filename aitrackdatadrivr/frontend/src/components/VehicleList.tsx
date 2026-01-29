import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Vehicle {
    VEICOD: number;
    VEIPLACA: string;
    VEI_DEVICE_ID?: string;
}

interface DirijabemUser {
    codusu: number;
    name: string;
}

interface VehicleListProps {
    selectedVehicleId: number | null;
    onVehicleSelect: (id: number | null) => void;
    selectedUserId: number | null;
    onUserSelect: (id: number | null) => void;
}

const VehicleList: React.FC<VehicleListProps> = ({
    selectedVehicleId,
    onVehicleSelect,
    selectedUserId,
    onUserSelect
}) => {
    const [trackerVehicles, setTrackerVehicles] = useState<Vehicle[]>([]);
    const [dirijabemUsers, setDirijabemUsers] = useState<DirijabemUser[]>([]);
    const [error, setError] = useState<string | null>(null);

    // Fetch TRACKER vehicles
    useEffect(() => {
        const fetchTrackerVehicles = async () => {
            try {
                const response = await axios.get<Vehicle[]>('http://localhost:5009/api/posicoes');
                const uniqueVehicles = Array.from(
                    new Map(response.data.map(v => [v.VEICOD, v])).values()
                );
                setTrackerVehicles(uniqueVehicles);
            } catch (err) {
                console.error('Error fetching tracker vehicles:', err);
            }
        };

        fetchTrackerVehicles();
        const intervalId = setInterval(fetchTrackerVehicles, 5000);

        return () => clearInterval(intervalId);
    }, []);

    // Fetch DIRIJABEM users
    useEffect(() => {
        const fetchDirijabemUsers = async () => {
            try {
                const response = await axios.get<DirijabemUser[]>('http://localhost:5009/api/dirijabem/users');
                setDirijabemUsers(response.data);
            } catch (err) {
                console.error('Error fetching dirijabem users:', err);
                setError('Falha ao carregar usuários Dirijabem');
            }
        };

        fetchDirijabemUsers();
    }, []);

    const handleTrackerSelect = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const vehicleId = event.target.value ? parseInt(event.target.value) : null;
        onVehicleSelect(vehicleId);
    };

    const handleDirijabemSelect = async (event: React.ChangeEvent<HTMLSelectElement>) => {
        const userId = event.target.value ? parseInt(event.target.value) : null;

        if (userId) {
            try {
                // Start/resume trip for selected user
                await axios.post(`http://localhost:5009/api/dirijabem/user/${userId}/start`);
                onUserSelect(userId);
            } catch (err) {
                console.error('Error starting trip:', err);
                setError('Falha ao iniciar viagem');
            }
        } else {
            onUserSelect(null);
        }
    };

    if (error) {
        return <div style={styles.error}>{error}</div>;
    }

    return (
        <div style={styles.container}>
            {/* TRACKER Section */}
            <div style={styles.section}>
                <h3 style={styles.sectionTitle}>🚗 TRACKER</h3>
                <select
                    style={styles.scrollableSelect}
                    value={selectedVehicleId?.toString() || ''}
                    onChange={handleTrackerSelect}
                >
                    <option value="">Selecione veículo...</option>
                    {trackerVehicles.map(vehicle => (
                        <option key={vehicle.VEICOD} value={vehicle.VEICOD}>
                            {vehicle.VEIPLACA} (ID: {vehicle.VEICOD})
                        </option>
                    ))}
                </select>
            </div>

            {/* DIRIJABEM Section */}
            <div style={styles.section}>
                <h3 style={styles.sectionTitle}>🏁 DIRIJABEM</h3>
                <select
                    style={styles.scrollableSelect}
                    value={selectedUserId?.toString() || ''}
                    onChange={handleDirijabemSelect}
                >
                    <option value="">Selecione usuário...</option>
                    {dirijabemUsers.map(user => (
                        <option key={user.codusu} value={user.codusu}>
                            {user.name}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        padding: '20px',
        backgroundColor: '#1f2937',
        color: 'white',
        height: '100%',
        overflowY: 'auto',
    },
    section: {
        marginBottom: '30px',
    },
    sectionTitle: {
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '12px',
        color: '#10b981',
        borderBottom: '2px solid #374151',
        paddingBottom: '8px',
    },
    scrollableSelect: {
        width: '100%',
        padding: '10px',
        backgroundColor: '#374151',
        color: '#f3f4f6',
        border: '1px solid #4b5563',
        borderRadius: '6px',
        fontSize: '14px',
        cursor: 'pointer',
        outline: 'none',
    } as React.CSSProperties,
    error: {
        padding: '10px',
        margin: '10px',
        backgroundColor: '#ef4444',
        color: 'white',
        borderRadius: '4px',
        fontSize: '14px',
    },
};

export default VehicleList;
