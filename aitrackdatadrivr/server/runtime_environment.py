"""Contrato autoritativo do ambiente operacional exibido aos operadores."""

import os
from datetime import datetime, timezone
from typing import Mapping, Optional


RUNTIME_SCHEMA_VERSION = 'runtime-environment.v1'
GLOBAL_MODE_VARIABLE = 'AITRACK_OPERATION_MODE'
SOURCE_MODE_VARIABLES = (
    ('tracker', 'Tracker', 'AITRACK_TRACKER_MODE'),
    ('dirijabem', 'Dirija Bem', 'AITRACK_DIRIJABEM_MODE'),
)

GLOBAL_MODES = {'production', 'simulation', 'replay'}
SOURCE_MODE_ALIASES = {
    'live': 'production',
    'production': 'production',
    'simulation': 'simulation',
    'synthetic': 'simulation',
    'replay': 'replay',
}


def _configured_value(environ: Mapping[str, str], name: str) -> Optional[str]:
    value = environ.get(name, '').strip().lower()
    return value or None


def build_runtime_environment(
    environ: Mapping[str, str] = os.environ,
    generated_at: Optional[datetime] = None,
) -> dict:
    """Agrega configuração global e por fonte sem presumir produção."""
    global_raw = _configured_value(environ, GLOBAL_MODE_VARIABLE)
    configured_mode = global_raw if global_raw in GLOBAL_MODES else None
    issues = []
    if global_raw is not None and configured_mode is None:
        issues.append('INVALID_GLOBAL_MODE')

    sources = []
    source_modes = []
    for source, label, variable in SOURCE_MODE_VARIABLES:
        raw_mode = _configured_value(environ, variable)
        mode = SOURCE_MODE_ALIASES.get(raw_mode or '', 'unknown')
        if raw_mode is not None and mode == 'unknown':
            issues.append(f'INVALID_{source.upper()}_MODE')
        sources.append({
            'source': source,
            'label': label,
            'mode': mode,
            'configured': raw_mode is not None and mode != 'unknown',
        })
        source_modes.append(mode)

    known_modes = {mode for mode in source_modes if mode != 'unknown'}
    if global_raw is not None and configured_mode is None:
        mode = 'unknown'
        authority = 'invalid_configuration'
    elif configured_mode == 'production':
        # Produção exige confirmação positiva das duas integrações. Isso impede
        # que uma variável global esconda replay/simulação ou fonte não configurada.
        if source_modes == ['production', 'production']:
            mode = 'production'
            authority = 'global_and_sources'
        elif known_modes - {'production'}:
            mode = 'mixed'
            authority = 'configuration_conflict'
            issues.append('GLOBAL_SOURCE_MODE_CONFLICT')
        else:
            mode = 'unknown'
            authority = 'unconfirmed_production'
            issues.append('PRODUCTION_SOURCES_UNCONFIRMED')
    elif configured_mode in {'simulation', 'replay'}:
        conflicting_modes = known_modes - {configured_mode}
        if conflicting_modes:
            mode = 'mixed'
            authority = 'configuration_conflict'
            issues.append('GLOBAL_SOURCE_MODE_CONFLICT')
        else:
            mode = configured_mode
            authority = 'global_configuration'
    elif 'unknown' in source_modes:
        mode = 'unknown'
        authority = 'incomplete_source_configuration'
        issues.append('SOURCE_MODE_UNCONFIRMED')
    elif known_modes == {'production'}:
        mode = 'unknown'
        authority = 'unconfirmed_production'
        issues.append('PRODUCTION_GLOBAL_UNCONFIRMED')
    elif len(known_modes) == 1:
        mode = next(iter(known_modes))
        authority = 'source_configuration'
    else:
        mode = 'mixed'
        authority = 'source_configuration'
        issues.append('SOURCE_MODES_DIFFER')

    timestamp = generated_at or datetime.now(timezone.utc)
    return {
        'schema_version': RUNTIME_SCHEMA_VERSION,
        'generated_at': timestamp.isoformat(),
        'mode': mode,
        'authority': authority,
        'safe_for_real_actions': mode == 'production',
        'sources': sources,
        'issues': issues,
    }
