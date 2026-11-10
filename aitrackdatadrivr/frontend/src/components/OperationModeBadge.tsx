import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { checkingOperationMode, resolveOperationMode } from '../config/operationMode';
import { runtimeEnvironmentService } from '../services/apiService';
import type { RuntimeEnvironment } from '../types/runtimeEnvironment';

interface OperationModeBadgeProps {
  refreshIntervalMs?: number;
}

const OperationModeBadge: React.FC<OperationModeBadgeProps> = ({
  refreshIntervalMs = 15000,
}) => {
  const [environment, setEnvironment] = useState<RuntimeEnvironment | null>(null);
  const [checking, setChecking] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const requestInFlight = useRef(false);

  const loadEnvironment = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    try {
      const response = await runtimeEnvironmentService.getCurrent();
      setEnvironment(response.data);
      setUnavailable(false);
    } catch {
      setUnavailable(true);
    } finally {
      setChecking(false);
      requestInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    loadEnvironment();
    const interval = window.setInterval(loadEnvironment, refreshIntervalMs);
    return () => window.clearInterval(interval);
  }, [loadEnvironment, refreshIntervalMs]);

  const generatedAtMs = environment ? Date.parse(environment.generated_at) : NaN;
  const stale = environment !== null && (
    !Number.isFinite(generatedAtMs) || Math.abs(Date.now() - generatedAtMs) > 30000
  );
  const effectiveMode = unavailable || stale ? 'unknown' : environment?.mode;
  const presentation = checking && environment === null
    ? checkingOperationMode()
    : resolveOperationMode(effectiveMode);
  const details = useMemo(() => {
    if (checking && environment === null) return presentation.description;
    if (unavailable) return 'Backend indisponível. O ambiente não pode ser confirmado.';
    if (stale) return 'O estado do ambiente está desatualizado há mais de 30 segundos.';
    if (!environment) return presentation.description;
    const sources = environment.sources
      .map(source => `${source.label}: ${resolveOperationMode(source.mode).label}`)
      .join(' · ');
    return `${presentation.description} ${sources}`;
  }, [checking, environment, presentation.description, stale, unavailable]);

  return (
    <span
      role="status"
      aria-label={`Ambiente: ${presentation.label}`}
      data-mode={presentation.mode}
      title={details}
      style={{
        alignItems: 'center',
        backgroundColor: presentation.backgroundColor,
        border: `1px solid ${presentation.color}`,
        borderRadius: '999px',
        color: presentation.color,
        display: 'inline-flex',
        fontSize: '10px',
        fontWeight: 800,
        letterSpacing: '0.06em',
        padding: '4px 8px',
        whiteSpace: 'nowrap',
      }}
    >
      AMBIENTE: {presentation.label}
    </span>
  );
};

export default OperationModeBadge;
