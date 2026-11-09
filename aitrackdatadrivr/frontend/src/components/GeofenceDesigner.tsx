import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import L from 'leaflet';
import { Circle, CircleMarker, Polygon, Polyline, Popup, useMap, useMapEvents } from 'react-leaflet';
import { geofenceService } from '../services/apiService';
import type {
  CreateGeofenceBody,
  UpdateGeofenceBody,
  Geofence,
  GeofenceGeometry,
  GeofenceRule,
  GeofenceAssignment,
  GeofenceAssignmentOptions,
  AssignmentTargetType,
} from '../types/geofence';
import './GeofenceDesigner.css';

type LatLngTuple = [number, number];
type DrawMode = 'circle' | 'polygon' | null;

interface CircleDraft {
  type: 'circle';
  center: LatLngTuple;
  radius: number;
}

interface PolygonDraft {
  type: 'polygon';
  points: LatLngTuple[];
}

type GeofenceDraft = CircleDraft | PolygonDraft;

const RULE_COLORS: Record<GeofenceRule, string> = {
  allowed: '#2563eb',
  forbidden: '#dc2626',
};
const STATUS_LABELS = {
  draft: 'Rascunho', active: 'Ativa', inactive: 'Inativa', archived: 'Arquivada',
};
const TARGET_LABELS: Record<AssignmentTargetType, string> = {
  vehicle: 'Veículo', driver: 'Motorista', group: 'Grupo',
};

const localOperatorId = () => {
  const stored = window.localStorage.getItem('aitrack.operator.id');
  if (stored) return stored;
  const created = `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem('aitrack.operator.id', created);
  return created;
};

export function draftToApiGeometry(draft: GeofenceDraft): GeofenceGeometry {
  if (draft.type === 'circle') {
    return {
      type: 'Circle',
      center: [draft.center[1], draft.center[0]],
      radius_meters: Math.round(draft.radius * 100) / 100,
    };
  }
  if (draft.points.length < 3) throw new Error('Polígono precisa de ao menos três vértices.');
  const ring = draft.points.map(([lat, lng]): [number, number] => [lng, lat]);
  ring.push([...ring[0]] as [number, number]);
  return { type: 'Polygon', coordinates: [ring] };
}

const formatDistance = (meters: number) => (
  meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${Math.round(meters)} m`
);

const geometryPositions = (geometry: GeofenceGeometry): LatLngTuple[] => {
  if (geometry.type === 'Circle') return [];
  return geometry.coordinates[0].map(([lng, lat]) => [lat, lng]);
};

const geometryToDraft = (geometry: GeofenceGeometry): GeofenceDraft => {
  if (geometry.type === 'Circle') {
    return {
      type: 'circle',
      center: [geometry.center[1], geometry.center[0]],
      radius: geometry.radius_meters,
    };
  }
  const points = geometryPositions(geometry);
  const withoutClosingPoint = points.length > 1
    && points[0][0] === points[points.length - 1][0]
    && points[0][1] === points[points.length - 1][1]
    ? points.slice(0, -1)
    : points;
  return { type: 'polygon', points: withoutClosingPoint };
};

const ExistingGeofence: React.FC<{ geofence: Geofence }> = ({ geofence }) => {
  const baseColor = geofence.status === 'active' ? RULE_COLORS[geofence.regra] : '#64748b';
  const pathOptions = {
    color: baseColor,
    fillColor: baseColor,
    fillOpacity: geofence.status === 'active' ? 0.14 : 0.06,
    weight: 2,
    dashArray: geofence.status === 'active' ? undefined : '6 6',
  };
  const popup = (
    <Popup>
      <strong>{geofence.nome}</strong><br />
      {geofence.regra === 'allowed' ? 'Área permitida' : 'Área proibida'} · {STATUS_LABELS[geofence.status]}<br />
      Versão geométrica {geofence.geometry_version}
    </Popup>
  );
  if (geofence.geometry.type === 'Circle') {
    const [lng, lat] = geofence.geometry.center;
    return <Circle center={[lat, lng]} radius={geofence.geometry.radius_meters} pathOptions={pathOptions}>{popup}</Circle>;
  }
  return <Polygon positions={geometryPositions(geofence.geometry)} pathOptions={pathOptions}>{popup}</Polygon>;
};

const GeofenceDesigner: React.FC = () => {
  const map = useMap();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<DrawMode>(null);
  const [draft, setDraft] = useState<GeofenceDraft | null>(null);
  const [cursor, setCursor] = useState<LatLngTuple | null>(null);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [regra, setRegra] = useState<GeofenceRule>('allowed');
  const [status, setStatus] = useState<'draft' | 'active' | 'inactive'>('draft');
  const [operatorName, setOperatorName] = useState(
    () => window.localStorage.getItem('aitrack.operator.name') || '',
  );
  const [operatorId] = useState(localOperatorId);
  const [editingFence, setEditingFence] = useState<Geofence | null>(null);
  const [changeReason, setChangeReason] = useState('');
  const [assignmentOptions, setAssignmentOptions] = useState<GeofenceAssignmentOptions | null>(null);
  const [assignments, setAssignments] = useState<GeofenceAssignment[]>([]);
  const [targetType, setTargetType] = useState<AssignmentTargetType>('vehicle');
  const [targetId, setTargetId] = useState('');
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [showGroupForm, setShowGroupForm] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [groupVehicleIds, setGroupVehicleIds] = useState<number[]>([]);
  const [groupDriverIds, setGroupDriverIds] = useState<number[]>([]);

  const loadGeofences = useCallback(async () => {
    try {
      const response = await geofenceService.getAll({ limit: 200 });
      setGeofences(response.data.geofences);
    } catch {
      setMessage({ type: 'error', text: 'Não foi possível carregar as cercas existentes.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadGeofences(); }, [loadGeofences]);

  useEffect(() => {
    if (!panelRef.current) return;
    L.DomEvent.disableClickPropagation(panelRef.current);
    L.DomEvent.disableScrollPropagation(panelRef.current);
  }, [open]);

  const cancelDrawing = useCallback(() => {
    setMode(null);
    setDraft(editingFence ? geometryToDraft(editingFence.geometry) : null);
    setCursor(null);
    setMessage(null);
  }, [editingFence]);

  const clearForm = useCallback(() => {
    setEditingFence(null);
    setMode(null);
    setDraft(null);
    setCursor(null);
    setNome('');
    setDescricao('');
    setRegra('allowed');
    setStatus('draft');
    setChangeReason('');
    setMessage(null);
  }, []);

  const beginEdit = (fence: Geofence) => {
    if (fence.status === 'archived') return;
    setOpen(true);
    setEditingFence(fence);
    setMode(null);
    setDraft(geometryToDraft(fence.geometry));
    setCursor(null);
    setNome(fence.nome);
    setDescricao(fence.descricao || '');
    setRegra(fence.regra);
    setStatus(fence.status);
    setChangeReason('');
    setMessage(null);
    setAssignmentBusy(true);
    Promise.all([
      geofenceService.getAssignmentOptions(),
      geofenceService.getAssignments(fence.public_id),
    ]).then(([optionsResponse, assignmentsResponse]) => {
      setAssignmentOptions(optionsResponse.data);
      setAssignments(assignmentsResponse.data.assignments);
    }).catch(() => {
      setMessage({ type: 'error', text: 'Não foi possível carregar as atribuições.' });
    }).finally(() => setAssignmentBusy(false));
  };

  const optionList = assignmentOptions
    ? targetType === 'vehicle' ? assignmentOptions.vehicles
      : targetType === 'driver' ? assignmentOptions.drivers : assignmentOptions.groups
    : [];

  const assignTarget = async () => {
    if (!editingFence || !targetId || !operatorName.trim()) {
      setMessage({ type: 'error', text: 'Selecione o alvo e informe o operador.' });
      return;
    }
    setAssignmentBusy(true);
    setMessage(null);
    try {
      const response = await geofenceService.assign(editingFence.public_id, {
        target_type: targetType,
        target_id: Number(targetId),
        operator: { id: operatorId, name: operatorName.trim() },
      });
      setAssignments(previous => [...previous, response.data.assignment]);
      setEditingFence(previous => previous ? {
        ...previous, active_assignments: previous.active_assignments + 1,
      } : previous);
      setGeofences(previous => previous.map(fence => fence.public_id === editingFence.public_id
        ? { ...fence, active_assignments: fence.active_assignments + 1 } : fence));
      setTargetId('');
      setMessage({ type: 'success', text: 'Alvo atribuído à cerca.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error?.response?.data?.error || 'Não foi possível atribuir o alvo.' });
    } finally {
      setAssignmentBusy(false);
    }
  };

  const deactivateAssignment = async (assignment: GeofenceAssignment) => {
    if (!editingFence || !operatorName.trim()) return;
    setAssignmentBusy(true);
    try {
      await geofenceService.deactivateAssignment(editingFence.public_id, assignment.id, {
        expected_version: assignment.version,
        operator: { id: operatorId, name: operatorName.trim() },
      });
      setAssignments(previous => previous.filter(item => item.id !== assignment.id));
      setEditingFence(previous => previous ? {
        ...previous, active_assignments: Math.max(0, previous.active_assignments - 1),
      } : previous);
      setGeofences(previous => previous.map(fence => fence.public_id === editingFence.public_id
        ? { ...fence, active_assignments: Math.max(0, fence.active_assignments - 1) } : fence));
      setMessage({ type: 'success', text: 'Atribuição desativada.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error?.response?.data?.error || 'Não foi possível desativar a atribuição.' });
    } finally {
      setAssignmentBusy(false);
    }
  };

  const createGroup = async () => {
    if (!groupName.trim() || !operatorName.trim() || (!groupVehicleIds.length && !groupDriverIds.length)) {
      setMessage({ type: 'error', text: 'Informe nome, operador e ao menos um membro do grupo.' });
      return;
    }
    setAssignmentBusy(true);
    try {
      const response = await geofenceService.createGroup({
        nome: groupName.trim(), vehicle_ids: groupVehicleIds, driver_ids: groupDriverIds,
        operator: { id: operatorId, name: operatorName.trim() },
      });
      setAssignmentOptions(previous => previous ? {
        ...previous, groups: [...previous.groups, response.data.group],
      } : previous);
      setTargetType('group');
      setTargetId(String(response.data.group.id));
      setGroupName(''); setGroupVehicleIds([]); setGroupDriverIds([]); setShowGroupForm(false);
      setMessage({ type: 'success', text: 'Grupo criado; confirme a atribuição abaixo.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error?.response?.data?.error || 'Não foi possível criar o grupo.' });
    } finally {
      setAssignmentBusy(false);
    }
  };

  useEffect(() => {
    const container = map.getContainer();
    const wasDoubleClickEnabled = map.doubleClickZoom.enabled();
    if (mode) {
      container.style.cursor = 'crosshair';
      container.classList.add('geofence-drawing');
      map.doubleClickZoom.disable();
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && mode) cancelDrawing();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      container.style.cursor = '';
      container.classList.remove('geofence-drawing');
      if (wasDoubleClickEnabled) map.doubleClickZoom.enable();
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [cancelDrawing, map, mode]);

  useMapEvents({
    click(event) {
      if (mode === 'circle') {
        if (!draft || draft.type !== 'circle') {
          setDraft({ type: 'circle', center: [event.latlng.lat, event.latlng.lng], radius: 0 });
          setMessage(null);
          return;
        }
        const radius = map.distance(draft.center, event.latlng);
        if (radius < 5 || radius > 100_000) {
          setMessage({ type: 'error', text: 'O raio deve ficar entre 5 metros e 100 km.' });
          return;
        }
        setDraft({ ...draft, radius });
        setMode(null);
        setCursor(null);
      } else if (mode === 'polygon') {
        const point: LatLngTuple = [event.latlng.lat, event.latlng.lng];
        setDraft(previous => previous?.type === 'polygon'
          ? { ...previous, points: [...previous.points, point] }
          : { type: 'polygon', points: [point] });
        setMessage(null);
      }
    },
    mousemove(event) {
      if (mode) setCursor([event.latlng.lat, event.latlng.lng]);
    },
  });

  const startDrawing = (nextMode: Exclude<DrawMode, null>) => {
    setOpen(true);
    setMode(nextMode);
    setDraft(nextMode === 'polygon' ? { type: 'polygon', points: [] } : null);
    setCursor(null);
    setMessage(null);
  };

  const finishPolygon = () => {
    if (!draft || draft.type !== 'polygon' || draft.points.length < 3) {
      setMessage({ type: 'error', text: 'Marque ao menos três vértices para concluir.' });
      return;
    }
    setMode(null);
    setCursor(null);
  };

  const undoPoint = () => {
    if (!draft || draft.type !== 'polygon') return;
    setDraft({ ...draft, points: draft.points.slice(0, -1) });
  };

  const save = async () => {
    if (!draft || (draft.type === 'circle' && draft.radius <= 0)) {
      setMessage({ type: 'error', text: 'Desenhe e conclua a geometria antes de salvar.' });
      return;
    }
    if (mode) {
      setMessage({ type: 'error', text: 'Conclua o desenho antes de salvar.' });
      return;
    }
    if (!nome.trim()) {
      setMessage({ type: 'error', text: 'Informe um nome para a cerca.' });
      return;
    }
    if (!operatorName.trim()) {
      setMessage({ type: 'error', text: 'Informe o nome do operador responsável.' });
      return;
    }
    if (editingFence && changeReason.trim().length < 3) {
      setMessage({ type: 'error', text: 'Informe o motivo da alteração.' });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const body: CreateGeofenceBody = {
        nome: nome.trim(),
        descricao: descricao.trim() || undefined,
        regra,
        status,
        geometry: draftToApiGeometry(draft),
        operator: { id: operatorId, name: operatorName.trim() },
        change_reason: editingFence ? changeReason.trim() : 'Criação visual no mapa',
      };
      const response = editingFence
        ? await geofenceService.update(editingFence.public_id, {
            ...body,
            expected_version: editingFence.version,
          } as UpdateGeofenceBody)
        : await geofenceService.create(body);
      window.localStorage.setItem('aitrack.operator.name', operatorName.trim());
      setGeofences(previous => editingFence
        ? previous.map(fence => fence.public_id === editingFence.public_id ? response.data.geofence : fence)
        : [response.data.geofence, ...previous]);
      const action = editingFence ? 'atualizada' : 'salva';
      clearForm();
      setMessage({ type: 'success', text: `Cerca “${response.data.geofence.nome}” ${action} com sucesso.` });
    } catch (error: any) {
      const detail = error?.response?.data?.error;
      setMessage({ type: 'error', text: detail || 'Não foi possível salvar a cerca.' });
    } finally {
      setSaving(false);
    }
  };

  const archive = async () => {
    if (!editingFence) return;
    if (editingFence.active_assignments > 0) {
      setMessage({ type: 'error', text: 'Desative as atribuições antes de arquivar a cerca.' });
      return;
    }
    if (!operatorName.trim() || changeReason.trim().length < 3) {
      setMessage({ type: 'error', text: 'Informe operador e motivo antes de arquivar.' });
      return;
    }
    if (!window.confirm(`Arquivar a cerca “${editingFence.nome}”? O histórico será preservado.`)) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await geofenceService.archive(editingFence.public_id, {
        expected_version: editingFence.version,
        operator: { id: operatorId, name: operatorName.trim() },
        change_reason: changeReason.trim(),
      });
      setGeofences(previous => previous.map(fence => (
        fence.public_id === editingFence.public_id ? response.data.geofence : fence
      )));
      clearForm();
      setMessage({ type: 'success', text: 'Cerca arquivada. O histórico foi preservado.' });
    } catch (error: any) {
      const detail = error?.response?.data?.error;
      setMessage({ type: 'error', text: detail || 'Não foi possível arquivar a cerca.' });
    } finally {
      setSaving(false);
    }
  };

  const circlePreviewRadius = useMemo(() => {
    if (mode !== 'circle' || !draft || draft.type !== 'circle' || !cursor) return null;
    return map.distance(draft.center, cursor);
  }, [cursor, draft, map, mode]);
  const polygonPreview = draft?.type === 'polygon'
    ? [...draft.points, ...(mode === 'polygon' && cursor ? [cursor] : [])]
    : [];
  const drawingColor = RULE_COLORS[regra];

  const panel = (
    <div className="geofence-tool" ref={panelRef}>
      {!open ? (
        <button type="button" className="geofence-launcher" onClick={() => setOpen(true)}>
          ⬡ Criar cerca
        </button>
      ) : (
        <section className="geofence-panel" aria-label="Desenhar cerca eletrônica">
          <div className="geofence-heading">
            <div><h2>{editingFence ? 'Editar cerca' : 'Cerca eletrônica'}</h2><span className="geofence-help">{loading ? 'Carregando…' : `${geofences.length} cadastrada(s)`}</span></div>
            <button type="button" className="geofence-close" aria-label="Fechar desenho de cerca" onClick={() => { cancelDrawing(); setOpen(false); }}>×</button>
          </div>
          <p className="geofence-help">
            Círculo: clique no centro e depois na borda. Polígono: clique em cada vértice, sem cruzar linhas, e conclua no painel. `Esc` cancela.
          </p>
          <label className="geofence-field">Gerenciar cerca existente
            <select aria-label="Gerenciar cerca existente" value={editingFence?.public_id || ''}
              onChange={event => {
                const fence = geofences.find(item => item.public_id === event.target.value);
                if (fence) beginEdit(fence); else clearForm();
              }}>
              <option value="">Nova cerca</option>
              {geofences.map(fence => (
                <option key={fence.public_id} value={fence.public_id} disabled={fence.status === 'archived'}>
                  {fence.nome} — {STATUS_LABELS[fence.status]}
                </option>
              ))}
            </select>
          </label>
          <div className="geofence-row">
            <button type="button" className={`geofence-mode ${mode === 'circle' ? 'active' : ''}`} onClick={() => startDrawing('circle')} disabled={saving}>◯ Círculo</button>
            <button type="button" className={`geofence-mode ${mode === 'polygon' ? 'active' : ''}`} onClick={() => startDrawing('polygon')} disabled={saving}>⬡ Polígono</button>
          </div>
          {mode === 'polygon' && (
            <div className="geofence-actions">
              <button type="button" className="geofence-secondary" onClick={undoPoint} disabled={!draft || draft.type !== 'polygon' || draft.points.length === 0}>Desfazer ponto</button>
              <button type="button" className="geofence-primary" onClick={finishPolygon} disabled={!draft || draft.type !== 'polygon' || draft.points.length < 3}>Concluir polígono</button>
            </div>
          )}
          {mode && <button type="button" className="geofence-danger" style={{ marginTop: 9 }} onClick={cancelDrawing}>Cancelar desenho</button>}
          {draft && (
            <p className="geofence-summary">
              {draft.type === 'circle'
                ? `Raio: ${formatDistance(circlePreviewRadius ?? draft.radius)}`
                : `${draft.points.length} vértice(s) marcado(s)`}
            </p>
          )}
          <label className="geofence-field">Nome
            <input aria-label="Nome da cerca" maxLength={150} value={nome} onChange={event => setNome(event.target.value)} placeholder="Ex.: Garagem principal" />
          </label>
          <label className="geofence-field">Tipo de proteção
            <select aria-label="Tipo de proteção da cerca" value={regra} onChange={event => setRegra(event.target.value as GeofenceRule)}>
              <option value="allowed">Área permitida — alerta ao sair</option>
              <option value="forbidden">Área proibida — alerta ao entrar</option>
            </select>
          </label>
          <label className="geofence-field">Estado inicial
            <select aria-label="Estado inicial da cerca" value={status} onChange={event => setStatus(event.target.value as typeof status)}>
              <option value="draft">Rascunho — ainda não monitora</option>
              <option value="active">Ativa — requer atribuição para monitorar</option>
              <option value="inactive">Inativa</option>
            </select>
          </label>
          <label className="geofence-field">Descrição opcional
            <textarea aria-label="Descrição da cerca" rows={2} value={descricao} onChange={event => setDescricao(event.target.value)} />
          </label>
          <label className="geofence-field">Operador responsável
            <input aria-label="Operador responsável pela cerca" maxLength={150} value={operatorName} onChange={event => setOperatorName(event.target.value)} />
          </label>
          {editingFence && (
            <label className="geofence-field">Motivo da alteração
              <input aria-label="Motivo da alteração da cerca" maxLength={300} value={changeReason}
                onChange={event => setChangeReason(event.target.value)} placeholder="Ex.: Ajuste do limite operacional" />
            </label>
          )}
          {editingFence && <p className="geofence-help">Versão {editingFence.version} · geometria {editingFence.geometry_version} · {editingFence.active_assignments} atribuição(ões) ativa(s)</p>}
          {editingFence && (
            <section className="geofence-assignment-section" aria-label="Atribuições da cerca">
              <h3>Atribuições</h3>
              <p className="geofence-help">Escolha quem será avaliado quando o detector de cerca entrar em operação.</p>
              {assignments.map(assignment => (
                <div className="geofence-assignment-item" key={assignment.id}>
                  <span>{assignment.target_label}<small>{TARGET_LABELS[assignment.target_type]}</small></span>
                  <button type="button" className="geofence-danger" disabled={assignmentBusy}
                    onClick={() => deactivateAssignment(assignment)}>Remover</button>
                </div>
              ))}
              {!assignments.length && <p className="geofence-help">Nenhum alvo atribuído.</p>}
              <div className="geofence-row">
                <select aria-label="Tipo de alvo da cerca" value={targetType} onChange={event => { setTargetType(event.target.value as AssignmentTargetType); setTargetId(''); }}>
                  <option value="vehicle">Veículo</option>
                  <option value="driver">Motorista</option>
                  <option value="group">Grupo</option>
                </select>
                <select aria-label="Alvo da cerca" value={targetId} onChange={event => setTargetId(event.target.value)}>
                  <option value="">Selecione</option>
                  {optionList.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                </select>
              </div>
              <div className="geofence-actions">
                <button type="button" className="geofence-primary" disabled={assignmentBusy || !targetId} onClick={assignTarget}>Atribuir alvo</button>
                <button type="button" className="geofence-secondary" onClick={() => setShowGroupForm(value => !value)}>Criar grupo</button>
              </div>
              {showGroupForm && assignmentOptions && (
                <div className="geofence-group-form">
                  <label className="geofence-field">Nome do grupo
                    <input aria-label="Nome do grupo de monitoramento" value={groupName} onChange={event => setGroupName(event.target.value)} />
                  </label>
                  <label className="geofence-field">Veículos do grupo
                    <select aria-label="Veículos do grupo" multiple value={groupVehicleIds.map(String)}
                      onChange={event => setGroupVehicleIds(Array.from(event.target.selectedOptions).map(option => Number(option.value)))}>
                      {assignmentOptions.vehicles.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                    </select>
                  </label>
                  <label className="geofence-field">Motoristas do grupo
                    <select aria-label="Motoristas do grupo" multiple value={groupDriverIds.map(String)}
                      onChange={event => setGroupDriverIds(Array.from(event.target.selectedOptions).map(option => Number(option.value)))}>
                      {assignmentOptions.drivers.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                    </select>
                  </label>
                  <button type="button" className="geofence-primary" disabled={assignmentBusy} onClick={createGroup}>Salvar grupo</button>
                </div>
              )}
            </section>
          )}
          <div className="geofence-actions">
            <button type="button" className="geofence-primary" onClick={save} disabled={saving || Boolean(mode)}>{saving ? 'Salvando…' : editingFence ? 'Salvar alterações' : 'Salvar cerca'}</button>
            {draft && !mode && <button type="button" className="geofence-secondary" onClick={cancelDrawing} disabled={saving}>{editingFence ? 'Restaurar original' : 'Refazer desenho'}</button>}
            {editingFence && <button type="button" className="geofence-danger" onClick={archive} disabled={saving || editingFence.active_assignments > 0}>Arquivar</button>}
          </div>
          {message && <p role="status" className={`geofence-message ${message.type}`}>{message.text}</p>}
          <div className="geofence-legend">
            <span><i className="geofence-dot" style={{ background: RULE_COLORS.allowed }} />Permitida</span>
            <span><i className="geofence-dot" style={{ background: RULE_COLORS.forbidden }} />Proibida</span>
          </div>
        </section>
      )}
    </div>
  );

  return (
    <>
      {geofences.map(geofence => <ExistingGeofence key={geofence.public_id} geofence={geofence} />)}
      {draft?.type === 'circle' && (
        <Circle center={draft.center} radius={circlePreviewRadius ?? draft.radius} pathOptions={{ color: drawingColor, fillColor: drawingColor, fillOpacity: .2, dashArray: '5 5' }} />
      )}
      {polygonPreview.length >= 2 && <Polyline positions={polygonPreview} pathOptions={{ color: drawingColor, weight: 3, dashArray: '5 5' }} />}
      {draft?.type === 'polygon' && draft.points.length >= 3 && !mode && (
        <Polygon positions={draft.points} pathOptions={{ color: drawingColor, fillColor: drawingColor, fillOpacity: .2 }} />
      )}
      {draft?.type === 'polygon' && draft.points.map((point, index) => (
        <CircleMarker key={`${point[0]}-${point[1]}-${index}`} center={point} radius={index === 0 ? 6 : 4} pathOptions={{ color: drawingColor, fillColor: '#fff', fillOpacity: 1 }} />
      ))}
      {createPortal(panel, map.getContainer())}
    </>
  );
};

export default GeofenceDesigner;
