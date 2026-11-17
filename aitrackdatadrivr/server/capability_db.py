"""Consulta somente leitura do catálogo versionado de capacidades."""

import json
from datetime import datetime
from typing import Dict, List, Optional

from .monitor_db import get_connection


def _serialize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def list_profiles(
    protocol: Optional[str] = None,
    device_model: Optional[str] = None,
    active_only: bool = True,
) -> List[Dict]:
    """Lista versões e itens sem inferir capacidade ausente."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        conditions = []
        params = []
        if protocol:
            conditions.append('p.protocol_code = %s')
            params.append(protocol.lower())
        if device_model:
            conditions.append('p.device_model IN (%s, %s)')
            params.extend([device_model, '*'])
        if active_only:
            conditions.append("p.status = 'active'")
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ''
        cursor.execute(
            "SELECT p.id, p.protocol_code, p.device_model, p.version_number, "
            "p.status, p.evidence_source, p.notes, p.created_by, p.created_at "
            f"FROM monitoramento.capability_profiles p{where} "
            "ORDER BY p.protocol_code, "
            "CASE WHEN p.device_model = '*' THEN 1 ELSE 0 END, "
            "p.device_model, p.version_number DESC",
            params,
        )
        profiles = cursor.fetchall()
        if not profiles:
            return []

        profile_ids = [profile['id'] for profile in profiles]
        placeholders = ','.join(['%s'] * len(profile_ids))
        cursor.execute(
            "SELECT profile_id, capability_code, capability_type, support_status, "
            "normalized_field, value_type, unit, evidence, constraints_json "
            "FROM monitoramento.capability_profile_items "
            f"WHERE profile_id IN ({placeholders}) "
            "ORDER BY capability_type, capability_code",
            profile_ids,
        )
        items_by_profile = {profile_id: [] for profile_id in profile_ids}
        for item in cursor.fetchall():
            constraints = item.pop('constraints_json', None)
            item['constraints'] = json.loads(constraints) if constraints else None
            items_by_profile[item.pop('profile_id')].append(item)

        result = []
        for profile in profiles:
            serialized = {key: _serialize(value) for key, value in profile.items()}
            serialized['capabilities'] = items_by_profile[profile['id']]
            result.append(serialized)
        return result
    finally:
        cursor.close()
        connection.close()


def resolve_profile(protocol: str, device_model: Optional[str] = None) -> Optional[Dict]:
    """Resolve o perfil exato mais recente, caindo apenas para o coringa explícito."""
    profiles = list_profiles(protocol=protocol, device_model=device_model, active_only=True)
    if not profiles:
        return None
    if device_model:
        exact = [profile for profile in profiles if profile['device_model'] == device_model]
        if exact:
            return max(exact, key=lambda profile: profile['version_number'])
    wildcard = [profile for profile in profiles if profile['device_model'] == '*']
    return max(wildcard, key=lambda profile: profile['version_number']) if wildcard else None
