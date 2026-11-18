import React, { useCallback, useEffect, useState } from 'react';
import AsyncDataState from './AsyncDataState';
import { detectorPolicyService, securityStateService, sensorService, unifiedVehicleService } from '../services/apiService';
import type { DetectorEpisodeDTO, DetectorPolicyDTO, VehicleSecurityStateDTO, VehicleSensorDTO, VehicleSensorsResponse } from '../types/sensor';

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
  const [policies, setPolicies] = useState<DetectorPolicyDTO[]>([]);
  const [securityState, setSecurityState] = useState<VehicleSecurityStateDTO | null>(null);
  const [episodes, setEpisodes] = useState<DetectorEpisodeDTO[]>([]);
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (selectedVehicleId === null && selectedUserId === null) {
      setData(null);
      setPolicies([]);
      setSecurityState(null);
      setEpisodes([]);
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
      const [sensorResponse, policyResponse, securityResponse, episodeResponse] = await Promise.all([
        sensorService.getByVehicle(vehicle.vehicle_id),
        detectorPolicyService.getAll(),
        securityStateService.getByVehicle(vehicle.vehicle_id),
        sensorService.getEpisodes(vehicle.vehicle_id),
      ]);
      setData(sensorResponse.data);
      setPolicies(policyResponse.data.policies);
      setSecurityState(securityResponse.data);
      setEpisodes(episodeResponse.data.episodes);
      setActionError(null);
      setState('idle');
    } catch (error) {
      console.error('Erro ao carregar sensores do veículo:', error);
      setData(null);
      setState('error');
    }
  }, [selectedUserId, selectedVehicleId]);

  const activatePolicy = async (policy: DetectorPolicyDTO, actor: string, reason: string) => {
    if (!data) return;
    setActionError(null);
    try {
      await detectorPolicyService.activate(policy.id, {
        actor,
        reason,
        correlation_id: `ui:vehicle:${data.vehicle.id}:policy:${policy.id}`,
      });
      const refreshed = await detectorPolicyService.getAll();
      setPolicies(refreshed.data.policies);
    } catch (error) {
      console.error('Erro ao ativar política de detecção:', error);
      setActionError('A política não foi ativada. Nenhum estado físico foi alterado.');
    }
  };

  const transitionSecurity = async (input: {
    target: 'armed' | 'disarmed'; operatorId: string; operatorName: string;
    basis: 'owner_request' | 'operator_protocol'; reason: string;
  }) => {
    if (!data || !securityState) return;
    setActionError(null);
    try {
      const response = await securityStateService.transition(data.vehicle.id, {
        target_state: input.target,
        expected_version: securityState.version,
        actor: { type: 'human', id: input.operatorId, name: input.operatorName },
        authorization_basis: input.basis,
        reason: input.reason,
        correlation_id: `ui:security:${data.vehicle.id}:${Date.now()}`,
      });
      setSecurityState(response.data);
    } catch (error) {
      console.error('Erro ao alterar estado patrimonial:', error);
      setActionError('Estado patrimonial não alterado. Recarregue para conferir versão e autorização.');
    }
  };

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
      {securityState && (
        <SecurityArmingControl state={securityState} onTransition={transitionSecurity} />
      )}
      <section aria-labelledby="detector-episodes-title" style={styles.episodeBox}>
        <strong id="detector-episodes-title">Episódios de tensão</strong>
        {episodes.length === 0 ? (
          <span>Nenhum episódio detectado. Políticas em rascunho não executam.</span>
        ) : episodes.slice(0, 10).map(episode => (
          <article key={episode.id} style={styles.episodeRow}>
            <span style={episode.status === 'open' ? styles.episodeOpen : styles.episodeResolved}>
              {episode.status === 'open' ? 'ABERTO' : 'RESOLVIDO'}
            </span>
            <strong>{episodeLabel(episode.episode_type)}</strong>
            <span>{episodeEvidence(episode)} · {episode.evidence_count} evidências · política {episode.policy_key} v{episode.version_number}</span>
          </article>
        ))}
      </section>
      <div style={styles.commandNotice}>
        <strong>Comandos físicos</strong>
        {data.confirmed_commands.length === 0
          ? <span>Nenhum comando físico confirmado para este protocolo; nenhum botão de bloqueio ou acionamento é exibido.</span>
          : <span>{data.confirmed_commands.length} capacidade(s) confirmada(s), ainda sujeitas ao contrato seguro de comando.</span>}
      </div>
      {actionError && <div role="alert" style={styles.actionError}>{actionError}</div>}
      <div style={styles.grid}>
        {data.sensors.map(sensor => (
          <SensorCard
            key={sensor.id}
            sensor={sensor}
            policies={policies.filter(policy => (
              policy.capability_code === sensor.capability_code
              && (policy.scope_type === 'global'
                || (policy.scope_type === 'source' && policy.scope_ref === sensor.source_code)
                || (policy.scope_type === 'vehicle' && policy.scope_ref === String(data.vehicle.id)))
            ))}
            onActivate={activatePolicy}
          />
        ))}
      </div>
    </section>
  );
};

const SecurityArmingControl: React.FC<{
  state: VehicleSecurityStateDTO;
  onTransition: (input: {
    target: 'armed' | 'disarmed'; operatorId: string; operatorName: string;
    basis: 'owner_request' | 'operator_protocol'; reason: string;
  }) => Promise<void>;
}> = ({ state, onTransition }) => {
  const [operatorId, setOperatorId] = useState('');
  const [operatorName, setOperatorName] = useState('');
  const [reason, setReason] = useState('');
  const [basis, setBasis] = useState<'owner_request' | 'operator_protocol'>('owner_request');
  const [busy, setBusy] = useState(false);
  const target = state.state === 'armed' ? 'disarmed' : 'armed';
  const valid = Boolean(
    operatorId.trim() && operatorName.trim() && reason.trim().length >= 5 && !busy,
  );
  return (
    <section aria-labelledby="security-state-title" style={styles.securityBox}>
      <div style={styles.securityHeader}>
        <div>
          <strong id="security-state-title">Monitoramento patrimonial</strong>
          <span style={styles.securityMeta}>Escopo: veículo {state.vehicle_id} · versão {state.version}</span>
        </div>
        <span style={state.state === 'armed' ? styles.armed : styles.disarmed}>
          {state.state === 'armed' ? 'ARMADO' : 'DESARMADO'}
        </span>
      </div>
      <span style={styles.securityMeta}>Última alteração: {state.changed_by.name} · {formatDate(state.changed_at)} · {state.reason}</span>
      <div style={styles.securityForm}>
        <input aria-label="ID do operador patrimonial" value={operatorId} onChange={event => setOperatorId(event.target.value)} placeholder="ID do operador" style={styles.input} />
        <input aria-label="Nome do operador patrimonial" value={operatorName} onChange={event => setOperatorName(event.target.value)} placeholder="Nome do operador" style={styles.input} />
        <select aria-label="Fundamento da autorização" value={basis} onChange={event => setBasis(event.target.value as typeof basis)} style={styles.input}>
          <option value="owner_request">Solicitação do proprietário</option>
          <option value="operator_protocol">Protocolo operacional</option>
        </select>
        <input aria-label="Motivo da transição patrimonial" value={reason} onChange={event => setReason(event.target.value)} placeholder="Motivo (mín. 5 caracteres)" style={styles.input} />
        <button
          type="button"
          disabled={!valid}
          style={{ ...styles.securityButton, opacity: valid ? 1 : 0.5 }}
          onClick={async () => {
            setBusy(true);
            await onTransition({
              target, operatorId: operatorId.trim(), operatorName: operatorName.trim(),
              basis, reason: reason.trim(),
            });
            setBusy(false);
          }}
        >{busy ? 'Alterando...' : `${target === 'armed' ? 'Armar' : 'Desarmar'} monitoramento patrimonial`}</button>
      </div>
      {state.history.length > 0 && (
        <details style={styles.history}>
          <summary>Histórico auditável ({state.history.length})</summary>
          {state.history.slice(0, 5).map(item => (
            <div key={item.id}>{item.from_state} → {item.to_state} · {item.actor_name} · {item.reason}</div>
          ))}
        </details>
      )}
    </section>
  );
};

const SensorCard: React.FC<{
  sensor: VehicleSensorDTO;
  policies: DetectorPolicyDTO[];
  onActivate: (policy: DetectorPolicyDTO, actor: string, reason: string) => Promise<void>;
}> = ({ sensor, policies, onActivate }) => (
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
    <PolicyControl policies={policies} onActivate={onActivate} />
  </article>
);

const PolicyControl: React.FC<{
  policies: DetectorPolicyDTO[];
  onActivate: (policy: DetectorPolicyDTO, actor: string, reason: string) => Promise<void>;
}> = ({ policies, onActivate }) => {
  const [actor, setActor] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const ordered = [...policies].sort((a, b) => b.version_number - a.version_number);
  const active = ordered.filter(policy => policy.status === 'active');
  const drafts = ordered.filter(policy => policy.status === 'draft');

  if (active.length === 0 && drafts.length === 0) {
    return (
      <div style={styles.policyBox}>
        <strong>Detecção não configurada</strong>
        <span>O sensor continua transmitindo; nenhum estado físico foi alterado.</span>
      </div>
    );
  }
  const canActivate = actor.trim().length > 0 && reason.trim().length >= 5 && !busy;
  return (
    <div style={styles.policyBox}>
      {active.map(policy => (
        <React.Fragment key={policy.id}>
          <strong>Detecção operacional ativa</strong>
          <span>Política {policy.policy_key} v{policy.version_number} · escopo {policy.scope_type}:{policy.scope_ref}. Isso não liga/desliga hardware.</span>
        </React.Fragment>
      ))}
      {drafts.length > 0 && (
        <>
          <strong>Políticas de detecção disponíveis</strong>
          <span>Ativam regras operacionais; não enviam comando ao equipamento.</span>
          <input aria-label="Operador da ativação" value={actor} onChange={event => setActor(event.target.value)} placeholder="Operador" style={styles.input} />
          <input aria-label="Motivo da ativação" value={reason} onChange={event => setReason(event.target.value)} placeholder="Motivo (mín. 5 caracteres)" style={styles.input} />
          {drafts.map(policy => (
            <button
              key={policy.id}
              type="button"
              disabled={!canActivate}
              style={{ ...styles.activateButton, opacity: canActivate ? 1 : 0.5 }}
              onClick={async () => {
                setBusy(true);
                await onActivate(policy, actor.trim(), reason.trim());
                setBusy(false);
              }}
            >{busy ? 'Ativando...' : `Ativar ${policy.policy_key} v${policy.version_number} (${policy.scope_type}:${policy.scope_ref})`}</button>
          ))}
        </>
      )}
    </div>
  );
};

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

function episodeLabel(type: DetectorEpisodeDTO['episode_type']): string {
  if (type === 'power_removed') return 'Alimentação removida';
  if (type === 'low_external_voltage') return 'Baixa tensão externa';
  return 'Veículo offline';
}

function episodeEvidence(episode: DetectorEpisodeDTO): string {
  if (episode.episode_type === 'offline') {
    return `${episode.trigger_value} s sem posição`;
  }
  return `${episode.minimum_value} V mín.`;
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
  commandNotice: { backgroundColor: '#2a2112', border: '1px solid #854d0e', borderRadius: '8px', display: 'flex', flexDirection: 'column', fontSize: '11px', gap: '4px', marginBottom: '12px', padding: '10px 12px' },
  episodeBox: { backgroundColor: '#172033', border: '1px solid #475569', borderRadius: '8px', display: 'flex', flexDirection: 'column', fontSize: '11px', gap: '7px', marginBottom: '12px', padding: '10px 12px' },
  episodeRow: { alignItems: 'center', borderTop: '1px solid #334155', display: 'grid', gap: '8px', gridTemplateColumns: '80px 160px 1fr', paddingTop: '7px' },
  episodeOpen: { backgroundColor: '#7f1d1d', borderRadius: '4px', color: '#fecaca', fontSize: '9px', fontWeight: 800, padding: '3px 5px', textAlign: 'center' },
  episodeResolved: { backgroundColor: '#065f46', borderRadius: '4px', color: '#a7f3d0', fontSize: '9px', fontWeight: 800, padding: '3px 5px', textAlign: 'center' },
  securityBox: { backgroundColor: '#10243b', border: '1px solid #2563eb', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px', padding: '12px' },
  securityHeader: { alignItems: 'center', display: 'flex', justifyContent: 'space-between' },
  securityMeta: { color: '#bfdbfe', display: 'block', fontSize: '10px', marginTop: '3px' },
  armed: { backgroundColor: '#7f1d1d', borderRadius: '999px', color: '#fecaca', fontSize: '10px', fontWeight: 900, padding: '5px 9px' },
  disarmed: { backgroundColor: '#374151', borderRadius: '999px', color: '#e5e7eb', fontSize: '10px', fontWeight: 900, padding: '5px 9px' },
  securityForm: { display: 'grid', gap: '6px', gridTemplateColumns: 'repeat(2, minmax(150px, 1fr))' },
  securityButton: { backgroundColor: '#1d4ed8', border: 'none', borderRadius: '4px', color: '#fff', cursor: 'pointer', fontSize: '10px', fontWeight: 800, padding: '7px' },
  history: { color: '#cbd5e1', fontSize: '10px' },
  actionError: { backgroundColor: '#450a0a', border: '1px solid #b91c1c', borderRadius: '6px', color: '#fecaca', marginBottom: '12px', padding: '9px' },
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
  policyBox: { backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', display: 'flex', flexDirection: 'column', fontSize: '10px', gap: '5px', marginTop: '12px', padding: '8px' },
  input: { backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '4px', color: '#f8fafc', fontSize: '10px', padding: '6px' },
  activateButton: { backgroundColor: '#047857', border: 'none', borderRadius: '4px', color: '#fff', cursor: 'pointer', fontSize: '10px', fontWeight: 700, padding: '7px' },
};

export default VehicleSensorsPanel;
