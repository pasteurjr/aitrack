import React, { useCallback, useEffect, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import { sensorService, unifiedVehicleService } from '../services/apiService';
import type { VehicleSensorDTO, VehicleSensorsResponse } from '../types/sensor';

interface VehicleSensorsPanelProps {
  selectedVehicleId: string | null;
  selectedUserId: number | null;
}

const LABELS: Record<string, string> = {
  position: 'Posição GPS', speed: 'Velocidade', heading: 'Direção',
  ignition: 'Ignição', external_voltage: 'Tensão externa',
  gps_valid: 'Validade do GPS', altitude: 'Altitude',
};

const VehicleSensorsPanel: React.FC<VehicleSensorsPanelProps> = ({
  selectedVehicleId,
  selectedUserId,
}) => {
  const [data, setData] = useState<VehicleSensorsResponse | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');

  const load = useCallback(async () => {
    if (selectedVehicleId === null && selectedUserId === null) {
      setData(null);
      setState('idle');
      return;
    }
    setState('loading');
    setData(null);
    try {
      const fleet = await unifiedVehicleService.getAll();
      const vehicle = fleet.data.vehicles.find(candidate => (
        (selectedVehicleId !== null && candidate.tracker?.device_id === selectedVehicleId)
        || (selectedUserId !== null && candidate.dirijabem?.codusu === selectedUserId)
      ));
      if (!vehicle) {
        setData(null);
        setState('error');
        return;
      }
      const response = await sensorService.getByVehicle(vehicle.vehicle_id);
      setData(response.data);
      setState('idle');
    } catch (error) {
      console.error('Erro ao carregar sensores do veículo:', error);
      setData(null);
      setState('error');
    }
  }, [selectedUserId, selectedVehicleId]);

  useEffect(() => { void load(); }, [load]);

  if (state === 'loading') {
    return <AsyncDataState variant="loading" message="Consultando sensores observados e capacidades comprovadas..." />;
  }
  if (state === 'error') {
    return <AsyncDataState variant="error" message="Não foi possível consultar os sensores sem fabricar dados." onRetry={() => { void load(); }} />;
  }
  if (!data || data.sensors.length === 0) {
    return (
      <AsyncDataState
        variant="empty"
        title="Nenhum sensor físico observado"
        message="Este veículo ainda não enviou uma leitura pelo pipeline normalizado. Eventos do Dirija Bem não são convertidos em sensores físicos."
      />
    );
  }

  return (
    <section aria-labelledby="vehicle-sensors-title" style={styles.container}>
      <header style={styles.header}>
        <div>
          <h2 id="vehicle-sensors-title" style={styles.title}>Sensores do veículo</h2>
          <p style={styles.subtitle}>Somente sinais observados e confirmados no catálogo operacional.</p>
        </div>
        <span style={styles.count}>{data.count} configurados</span>
      </header>
      <div style={styles.summary}>
        <span>Origem: {data.sources.join(', ')}</span>
        <span>Protocolo: {data.protocols.join(', ')}</span>
        <span>Placa: {data.vehicle.plate ?? 'não informada'}</span>
      </div>
      <div style={styles.grid}>
        {data.sensors.map(sensor => <SensorCard key={sensor.id} sensor={sensor} />)}
      </div>
    </section>
  );
};

const SensorCard: React.FC<{ sensor: VehicleSensorDTO }> = ({ sensor }) => (
  <article style={styles.card}>
    <div style={styles.cardTitleRow}>
      <strong style={styles.cardTitle}>{LABELS[sensor.capability_code] ?? sensor.capability_code}</strong>
      <span style={sensor.lifecycle_status === 'active' ? styles.active : styles.inactive}>
        {sensor.lifecycle_status === 'active' ? 'ATIVO' : 'INATIVO'}
      </span>
    </div>
    <div style={styles.badges}>
      <span style={styles.confirmed}>SUPORTE CONFIRMADO</span>
      <span style={styles.configured}>OBSERVADO</span>
      <span style={{ ...styles.health, ...HEALTH[sensor.health_status].style }}>
        {HEALTH[sensor.health_status].label}
      </span>
    </div>
    <div style={styles.value}>
      {formatValue(sensor)}
    </div>
    <dl style={styles.details}>
      <div><dt>Fonte</dt><dd>{sensor.source_code}</dd></div>
      <div><dt>Protocolo</dt><dd>{sensor.protocol_code}</dd></div>
      <div><dt>Unidade</dt><dd>{sensor.unit ?? 'sem unidade'}</dd></div>
      <div><dt>Qualidade</dt><dd>{sensor.latest_reading?.quality ?? 'indisponível'}</dd></div>
      <div><dt>Recebido</dt><dd>{formatDate(sensor.latest_reading?.received_at ?? sensor.last_seen_at)}</dd></div>
      <div><dt>Horário da fonte</dt><dd>{sensor.latest_reading?.observed_at ?? 'não informado'} (fuso não informado)</dd></div>
    </dl>
  </article>
);

const HEALTH: Record<VehicleSensorDTO['health_status'], { label: string; style: React.CSSProperties }> = {
  current: { label: 'ATUAL', style: { backgroundColor: '#065f46', color: '#a7f3d0' } },
  stale: { label: 'DESATUALIZADO', style: { backgroundColor: '#78350f', color: '#fde68a' } },
  invalid: { label: 'INVÁLIDO', style: { backgroundColor: '#7f1d1d', color: '#fecaca' } },
  unavailable: { label: 'INDISPONÍVEL', style: { backgroundColor: '#3f3f46', color: '#e4e4e7' } },
};

function formatValue(sensor: VehicleSensorDTO): string {
  const reading = sensor.latest_reading;
  if (!reading) return 'Sem leitura';
  if (reading.value_type === 'boolean') return reading.value ? 'Ligado / verdadeiro' : 'Desligado / falso';
  if (reading.value_type === 'geo' && typeof reading.value === 'object') {
    const value = reading.value as { latitude?: number; longitude?: number };
    return `${value.latitude?.toFixed(5) ?? '—'}, ${value.longitude?.toFixed(5) ?? '—'}`;
  }
  return `${String(reading.value)}${reading.unit ? ` ${reading.unit}` : ''}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'inválida' : date.toLocaleString('pt-BR');
}

const styles: Record<string, React.CSSProperties> = {
  container: { backgroundColor: '#0f172a', color: '#e5e7eb', height: '100%', overflowY: 'auto', padding: '20px' },
  header: { alignItems: 'center', display: 'flex', justifyContent: 'space-between' },
  title: { color: '#f8fafc', fontSize: '20px', margin: 0 },
  subtitle: { color: '#94a3b8', fontSize: '12px', margin: '5px 0 0' },
  count: { backgroundColor: '#064e3b', borderRadius: '999px', color: '#a7f3d0', fontSize: '11px', fontWeight: 800, padding: '6px 10px' },
  summary: { backgroundColor: '#172033', border: '1px solid #334155', borderRadius: '8px', display: 'flex', flexWrap: 'wrap', gap: '18px', margin: '16px 0', padding: '10px 12px', fontSize: '12px' },
  grid: { display: 'grid', gap: '12px', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' },
  card: { backgroundColor: '#172033', border: '1px solid #334155', borderRadius: '8px', padding: '13px' },
  cardTitleRow: { alignItems: 'center', display: 'flex', gap: '8px', justifyContent: 'space-between' },
  cardTitle: { color: '#f8fafc', fontSize: '14px' },
  active: { backgroundColor: '#065f46', borderRadius: '999px', color: '#a7f3d0', fontSize: '9px', fontWeight: 800, padding: '3px 6px' },
  inactive: { backgroundColor: '#3f3f46', borderRadius: '999px', color: '#d4d4d8', fontSize: '9px', padding: '3px 6px' },
  badges: { display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '9px' },
  confirmed: { backgroundColor: '#1e3a8a', borderRadius: '4px', color: '#bfdbfe', fontSize: '8px', fontWeight: 700, padding: '3px 5px' },
  configured: { backgroundColor: '#713f12', borderRadius: '4px', color: '#fde68a', fontSize: '8px', fontWeight: 700, padding: '3px 5px' },
  health: { borderRadius: '4px', fontSize: '8px', fontWeight: 800, padding: '3px 5px' },
  value: { color: '#f8fafc', fontSize: '20px', fontWeight: 800, marginTop: '12px', overflowWrap: 'anywhere' },
  details: { display: 'grid', gap: '7px', margin: '12px 0 0' },
};

export default VehicleSensorsPanel;
