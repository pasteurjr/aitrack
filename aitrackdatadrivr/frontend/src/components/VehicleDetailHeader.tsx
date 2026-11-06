import React, { useEffect, useMemo, useState } from 'react';
import { unifiedVehicleService } from '../services/apiService';
import type { UnifiedVehicleDTO } from '../types/unifiedVehicle';

interface VehicleDetailHeaderProps {
  selectedVehicleId: string | null;
  selectedUserId: number | null;
  onClear: () => void;
}

const VehicleDetailHeader: React.FC<VehicleDetailHeaderProps> = ({
  selectedVehicleId,
  selectedUserId,
  onClear,
}) => {
  const [vehicle, setVehicle] = useState<UnifiedVehicleDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const hasSelection = selectedVehicleId !== null || selectedUserId !== null;

  useEffect(() => {
    let cancelled = false;
    if (!hasSelection) {
      setVehicle(null);
      setError(false);
      return () => { cancelled = true; };
    }

    setLoading(true);
    setVehicle(null);
    setError(false);
    unifiedVehicleService.getAll()
      .then(response => {
        if (cancelled) return;
        const match = response.data.vehicles.find(candidate => (
          (selectedVehicleId !== null && candidate.tracker?.device_id === selectedVehicleId)
          || (selectedUserId !== null && candidate.dirijabem?.codusu === selectedUserId)
        ));
        setVehicle(match ?? null);
      })
      .catch(requestError => {
        console.error('Erro ao resolver cabeçalho do veículo:', requestError);
        if (!cancelled) {
          setVehicle(null);
          setError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [hasSelection, selectedUserId, selectedVehicleId]);

  const lastCommunication = useMemo(() => {
    if (!vehicle) return null;
    const values = vehicle.telemetry
      .map(item => item.last_communication_at)
      .filter((value): value is string => Boolean(value))
      .sort();
    return values.length > 0 ? values[values.length - 1] : null;
  }, [vehicle]);

  if (!hasSelection) return null;

  const rawIdentity = selectedVehicleId ?? `Usuário Dirija Bem ${selectedUserId}`;
  const modes = vehicle
    ? Array.from(new Set(vehicle.telemetry.map(item => item.mode))).join(' + ')
    : 'unknown';

  return (
    <section aria-labelledby="vehicle-detail-title" style={styles.container}>
      <div style={styles.identity}>
        <div style={styles.icon} aria-hidden="true">{vehicle?.identity_type === 'both' ? '🔗' : selectedVehicleId ? '🚗' : '🏁'}</div>
        <div>
          <h2 id="vehicle-detail-title" style={styles.title}>
            {loading ? 'Carregando identidade...' : vehicle?.display_name ?? rawIdentity}
          </h2>
          <div style={styles.subtitle}>
            {loading
              ? 'Resolvendo cadastro unificado...'
              : error
              ? 'Identidade indisponível'
              : vehicle
                ? [vehicle.plate, vehicle.tracker?.device_id, vehicle.dirijabem ? `CODUSU ${vehicle.dirijabem.codusu}` : null]
                    .filter(Boolean).join(' · ')
                : 'Identidade não vinculada ao cadastro unificado'}
          </div>
        </div>
      </div>

      <div style={styles.metadata}>
        {vehicle?.telemetry.map(item => (
          <span key={item.source} style={{ ...styles.sourceBadge, ...(item.source === 'tracker' ? styles.tracker : styles.dirijabem) }}>
            {item.source === 'tracker' ? 'TRACKER' : 'DIRIJA BEM'}
          </span>
        ))}
        <span style={styles.metaText}>Modo: {modes}</span>
        <span style={styles.metaText}>Último contato: {formatDate(lastCommunication)}</span>
        {vehicle && <span style={styles.metaText}>{vehicle.active ? 'Cadastro ativo' : 'Cadastro inativo'}</span>}
      </div>

      <button type="button" onClick={onClear} aria-label="Fechar detalhe do veículo" style={styles.closeButton}>×</button>
    </section>
  );
};

function formatDate(value: string | null): string {
  if (!value) return 'não informado';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'inválido' : date.toLocaleString('pt-BR');
}

const styles: Record<string, React.CSSProperties> = {
  container: { alignItems: 'center', backgroundColor: '#172033', borderBottom: '1px solid #475569', color: '#f8fafc', display: 'flex', flexShrink: 0, gap: '18px', minHeight: '66px', padding: '9px 14px' },
  identity: { alignItems: 'center', display: 'flex', gap: '10px', minWidth: '260px' },
  icon: { alignItems: 'center', backgroundColor: '#0f172a', borderRadius: '50%', display: 'flex', fontSize: '20px', height: '38px', justifyContent: 'center', width: '38px' },
  title: { fontSize: '14px', margin: 0 },
  subtitle: { color: '#94a3b8', fontSize: '10px', marginTop: '3px' },
  metadata: { alignItems: 'center', display: 'flex', flex: 1, flexWrap: 'wrap', gap: '7px' },
  sourceBadge: { borderRadius: '999px', fontSize: '9px', fontWeight: 800, padding: '3px 7px' },
  tracker: { backgroundColor: '#065f46', color: '#a7f3d0' },
  dirijabem: { backgroundColor: '#1e40af', color: '#bfdbfe' },
  metaText: { backgroundColor: '#273449', borderRadius: '4px', color: '#cbd5e1', fontSize: '10px', padding: '4px 7px' },
  closeButton: { background: 'transparent', border: 'none', color: '#cbd5e1', cursor: 'pointer', fontSize: '24px', padding: '4px 8px' },
};

export default VehicleDetailHeader;
