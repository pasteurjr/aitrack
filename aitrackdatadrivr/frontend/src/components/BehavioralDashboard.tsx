import React, { useCallback, useEffect, useRef, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import UnifiedFleetPanel from './UnifiedFleetPanel';
import type { UnifiedFleetItem } from './UnifiedFleetPanel';
import { dirijabemService, fleetService, trackerService } from '../services/apiService';

interface FleetStats {
    fleet_avg: number;
    total_vehicles: number;
    events_today: number;
    top3: Array<{ device_id: string; score: number }>;
    bottom3: Array<{ device_id: string; score: number }>;
}

interface VehicleScores {
    [device_id: string]: number;
}

interface TrackerVehicle {
    VEICOD: number;
    VEIPLACA: string;
    VEI_DEVICE_ID?: string;
}

interface DirijabemUser {
    codusu: number;
    name: string;
}

interface BehavioralDashboardProps {
    selectedVehicleId: string | null;
    onVehicleSelect: (deviceId: string | null) => void;
    selectedUserId: number | null;
    onUserSelect: (userId: number | null) => void;
}

const BehavioralDashboard: React.FC<BehavioralDashboardProps> = ({
    selectedVehicleId,
    onVehicleSelect,
    selectedUserId,
    onUserSelect
}) => {
    const [stats, setStats] = useState<FleetStats | null>(null);
    const [allVehicles, setAllVehicles] = useState<VehicleScores>({});
    const [trackerVehicles, setTrackerVehicles] = useState<TrackerVehicle[]>([]);
    const [dirijabemUsers, setDirijabemUsers] = useState<DirijabemUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [stale, setStale] = useState(false);
    const hasSuccessfulStats = useRef(false);
    const lastUpdatedRef = useRef<Date | null>(null);

    // Buscar veículos TRACKER
    useEffect(() => {
        const fetchTrackerVehicles = async () => {
            try {
                const response = await trackerService.getPositions<TrackerVehicle[]>();
                const uniqueVehicles = Array.from(
                    new Map(response.data.map(v => [v.VEICOD, v])).values()
                );
                setTrackerVehicles(uniqueVehicles);
            } catch (error) {
                console.error('Erro ao buscar veículos TRACKER:', error);
            }
        };

        fetchTrackerVehicles();
        const intervalId = setInterval(fetchTrackerVehicles, 5000);
        return () => clearInterval(intervalId);
    }, []);

    // Buscar usuários DIRIJABEM
    useEffect(() => {
        const fetchDirijabemUsers = async () => {
            try {
                const response = await dirijabemService.getUsers<DirijabemUser[]>();
                setDirijabemUsers(response.data);
            } catch (error) {
                console.error('Erro ao buscar usuários DIRIJABEM:', error);
            }
        };

        fetchDirijabemUsers();
    }, []);

    const fetchData = useCallback(async () => {
        try {
            const [statsResponse, scoresResponse] = await Promise.all([
                fleetService.getStats<FleetStats>(),
                fleetService.getScores<VehicleScores>(),
            ]);
            setStats(statsResponse.data);
            setAllVehicles(scoresResponse.data);
            setError(false);
            setStale(false);
            hasSuccessfulStats.current = true;
            lastUpdatedRef.current = new Date();
        } catch (requestError) {
            console.error("Erro ao buscar dados:", requestError);
            if (hasSuccessfulStats.current) {
                setStale(true);
            } else {
                setError(true);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    // Buscar stats e scores
    useEffect(() => {
        fetchData();
        const intervalId = setInterval(fetchData, 3000);
        return () => clearInterval(intervalId);
    }, [fetchData]);

    if (loading) {
        return (
            <div style={styles.container}>
                <AsyncDataState variant="loading" message="Consultando indicadores da frota..." />
            </div>
        );
    }

    if (error || !stats) {
        return (
            <div style={styles.container}>
                <AsyncDataState
                    variant="error"
                    message="Não foi possível carregar os indicadores da frota. Nenhum valor padrão foi exibido."
                    onRetry={fetchData}
                />
            </div>
        );
    }

    const handleTrackerSelect = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const deviceId = event.target.value || null;
        if (deviceId) onUserSelect(null);
        onVehicleSelect(deviceId);
    };

    const handleDirijabemSelect = async (event: React.ChangeEvent<HTMLSelectElement>) => {
        const userId = event.target.value ? parseInt(event.target.value) : null;

        console.log('[DIRIJABEM] Usuário selecionado:', userId);

        if (userId) {
            try {
                // Start/resume trip for selected user
                console.log('[DIRIJABEM] Iniciando viagem para usuário:', userId);
                const response = await dirijabemService.startUserTrip(userId);
                console.log('[DIRIJABEM] Resposta do servidor:', response.data);
                onVehicleSelect(null);
                onUserSelect(userId);
            } catch (error) {
                console.error('[DIRIJABEM] Erro ao iniciar viagem:', error);
            }
        } else {
            onUserSelect(null);
        }
    };

    const getScoreColor = (score: number): string => {
        if (score >= 75) return '#10b981';
        if (score >= 50) return '#f59e0b';
        return '#ef4444';
    };

    const greenCount = Object.values(stats).filter((v: any) => typeof v === 'number' && v >= 75).length;
    const yellowCount = Object.values(stats).filter((v: any) => typeof v === 'number' && v >= 50 && v < 75).length;
    const redCount = stats.total_vehicles - greenCount - yellowCount;
    const trackerByDeviceId = new Map(
        trackerVehicles.map(vehicle => [vehicle.VEI_DEVICE_ID || `VEI-${vehicle.VEICOD}`, vehicle])
    );
    const trackerIds = Array.from(new Set([
        ...Array.from(trackerByDeviceId.keys()),
        ...Object.keys(allVehicles),
    ])).sort();
    const unifiedFleetItems: UnifiedFleetItem[] = [
        ...trackerIds.map(deviceId => {
            const vehicle = trackerByDeviceId.get(deviceId);
            return {
                id: `tracker:${deviceId}`,
                source: 'tracker' as const,
                primaryLabel: vehicle?.VEIPLACA || deviceId,
                secondaryLabel: deviceId,
                score: allVehicles[deviceId] ?? null,
                sourceId: deviceId,
            };
        }),
        ...dirijabemUsers.map(user => ({
            id: `dirijabem:${user.codusu}`,
            source: 'dirijabem' as const,
            primaryLabel: user.name,
            secondaryLabel: `Usuário ${user.codusu}`,
            score: null,
            sourceId: user.codusu,
        })),
    ];
    const selectedUnifiedItemId = selectedVehicleId
        ? `tracker:${selectedVehicleId}`
        : selectedUserId
            ? `dirijabem:${selectedUserId}`
            : null;

    const handleUnifiedItemSelect = (item: UnifiedFleetItem) => {
        if (item.source === 'tracker') {
            onUserSelect(null);
            onVehicleSelect(String(item.sourceId));
            return;
        }

        // A visão unificada apenas consulta uma viagem já ativa; não inicia replay.
        onVehicleSelect(null);
        onUserSelect(Number(item.sourceId));
    };

    return (
        <div style={styles.container}>
            <h2 style={styles.title}>📊 Fleet Behavioral Dashboard</h2>

            {stale && (
                <AsyncDataState
                    variant="stale"
                    compact
                    message={`Falha na atualização. Exibindo a última resposta válida${lastUpdatedRef.current ? ` das ${lastUpdatedRef.current.toLocaleTimeString('pt-BR')}` : ''}.`}
                    onRetry={fetchData}
                />
            )}

            {/* TRACKER Section */}
            <div style={styles.selectSection}>
                <h3 style={styles.selectTitle}>🚗 TRACKER</h3>
                <select
                    style={styles.select}
                    value={selectedVehicleId || ''}
                    onChange={handleTrackerSelect}
                >
                    <option value="">Selecione veículo...</option>
                    {trackerVehicles.map(vehicle => (
                        <option key={vehicle.VEICOD} value={vehicle.VEI_DEVICE_ID || `VEI-${vehicle.VEICOD}`}>
                            {vehicle.VEIPLACA} ({vehicle.VEI_DEVICE_ID || `VEI-${vehicle.VEICOD}`})
                        </option>
                    ))}
                </select>
            </div>

            {/* DIRIJABEM Section */}
            <div style={styles.selectSection}>
                <h3 style={styles.selectTitle}>🏁 DIRIJABEM</h3>
                <select
                    style={styles.select}
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

            {/* KPI Cards */}
            <div style={styles.kpiContainer}>
                <div style={styles.kpiCard}>
                    <div style={styles.kpiLabel}>Score Médio</div>
                    <div style={{ ...styles.kpiValue, color: getScoreColor(stats.fleet_avg) }}>
                        {stats.fleet_avg.toFixed(1)}
                    </div>
                </div>

                <div style={styles.kpiCard}>
                    <div style={styles.kpiLabel}>Eventos Hoje</div>
                    <div style={styles.kpiValue}>{stats.events_today}</div>
                </div>

                <div style={styles.kpiCard}>
                    <div style={styles.kpiLabel}>Veículos com score</div>
                    <div style={styles.kpiValue}>{stats.total_vehicles}</div>
                </div>
            </div>

            {/* Top Performers */}
            <div style={styles.section}>
                <h3 style={styles.sectionTitle}>🏆 TOP PERFORMERS</h3>
                {stats.top3.map((vehicle, index) => (
                    <div key={vehicle.device_id} style={styles.vehicleRow}>
                        <span style={styles.rank}>{index + 1}.</span>
                        <span style={styles.deviceId}>{vehicle.device_id}</span>
                        <span style={{ ...styles.score, color: getScoreColor(vehicle.score) }}>
                            {vehicle.score.toFixed(1)}
                        </span>
                    </div>
                ))}
            </div>

            {/* Bottom Performers */}
            <div style={styles.section}>
                <h3 style={{ ...styles.sectionTitle, color: '#ef4444' }}>⚠️ NEEDS ATTENTION</h3>
                {stats.bottom3.reverse().map((vehicle, index) => (
                    <div key={vehicle.device_id} style={styles.vehicleRow}>
                        <span style={styles.rank}>{index + 1}.</span>
                        <span style={styles.deviceId}>{vehicle.device_id}</span>
                        <span style={{ ...styles.score, color: getScoreColor(vehicle.score) }}>
                            {vehicle.score.toFixed(1)}
                        </span>
                    </div>
                ))}
            </div>

            {/* Distribuição */}
            <div style={styles.section}>
                <h3 style={styles.sectionTitle}>📊 DISTRIBUIÇÃO</h3>
                <div style={styles.distItem}>
                    <span>🟢 Excelente (75+)</span>
                    <div style={styles.barContainer}>
                        <div style={{ ...styles.bar, width: `${(greenCount / stats.total_vehicles) * 100}%`, backgroundColor: '#10b981' }} />
                    </div>
                    <span>{greenCount}</span>
                </div>
                <div style={styles.distItem}>
                    <span>🟡 Moderado (50-74)</span>
                    <div style={styles.barContainer}>
                        <div style={{ ...styles.bar, width: `${(yellowCount / stats.total_vehicles) * 100}%`, backgroundColor: '#f59e0b' }} />
                    </div>
                    <span>{yellowCount}</span>
                </div>
                <div style={styles.distItem}>
                    <span>🔴 Crítico (0-49)</span>
                    <div style={styles.barContainer}>
                        <div style={{ ...styles.bar, width: `${(redCount / stats.total_vehicles) * 100}%`, backgroundColor: '#ef4444' }} />
                    </div>
                    <span>{redCount}</span>
                </div>
            </div>

            <UnifiedFleetPanel
                items={unifiedFleetItems}
                selectedItemId={selectedUnifiedItemId}
                onItemSelect={handleUnifiedItemSelect}
            />
        </div>
    );
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        backgroundColor: '#1f2937',
        color: 'white',
        padding: '20px',
        overflowY: 'auto',
        height: '100%',
    },
    title: {
        fontSize: '18px',
        fontWeight: 'bold',
        marginBottom: '20px',
        borderBottom: '2px solid #374151',
        paddingBottom: '10px',
    },
    selectSection: {
        marginBottom: '20px',
    },
    selectTitle: {
        fontSize: '14px',
        fontWeight: 'bold',
        marginBottom: '8px',
        color: '#10b981',
    },
    select: {
        width: '100%',
        padding: '10px',
        backgroundColor: '#374151',
        color: '#f3f4f6',
        border: '1px solid #4b5563',
        borderRadius: '6px',
        fontSize: '14px',
        cursor: 'pointer',
        outline: 'none',
    },
    kpiContainer: {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        marginBottom: '20px',
    },
    kpiCard: {
        backgroundColor: '#374151',
        padding: '15px',
        borderRadius: '8px',
        textAlign: 'center',
    },
    kpiLabel: {
        fontSize: '12px',
        color: '#9ca3af',
        marginBottom: '5px',
    },
    kpiValue: {
        fontSize: '24px',
        fontWeight: 'bold',
    },
    section: {
        marginBottom: '25px',
    },
    sectionTitle: {
        fontSize: '14px',
        fontWeight: 'bold',
        marginBottom: '10px',
        color: '#10b981',
    },
    vehicleRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 10px',
        backgroundColor: '#374151',
        borderRadius: '4px',
        marginBottom: '5px',
        fontSize: '13px',
    },
    rank: {
        width: '20px',
        color: '#9ca3af',
    },
    deviceId: {
        flex: 1,
        marginLeft: '10px',
    },
    score: {
        fontWeight: 'bold',
        fontSize: '14px',
    },
    distItem: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '10px',
        fontSize: '12px',
        gap: '10px',
    },
    barContainer: {
        flex: 1,
        height: '8px',
        backgroundColor: '#374151',
        borderRadius: '4px',
        overflow: 'hidden',
    },
    bar: {
        height: '100%',
        transition: 'width 0.3s ease',
    },
};

export default BehavioralDashboard;
