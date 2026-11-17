"""Persistência tipada e idempotente de sensores e leituras operacionais."""

import json
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional


TRACKER_FIELDS = {
    'position': ('geo', None),
    'speed': ('number', 'km/h'),
    'heading': ('number', 'degree'),
    'ignition': ('boolean', None),
    'external_voltage': ('number', 'V'),
    'gps_valid': ('boolean', None),
    'altitude': ('number', 'm'),
}


def _naive_utc(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime):
        raise ValueError('observed_at deve ser datetime ou ISO-8601')
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _resolve_vehicle_id(cursor, tracker_vehicle_id: int, device_id: Optional[str]):
    identities = [('vehicle_id', str(tracker_vehicle_id))]
    if device_id:
        identities.insert(0, ('device_id', str(device_id)))
    conditions = ' OR '.join(
        '(tipo_identidade = %s AND valor_externo = %s)' for _item in identities
    )
    params = []
    for identity_type, value in identities:
        params.extend([identity_type, value])
    cursor.execute(
        "SELECT vehicle_id FROM monitoramento.veiculo_identidades "
        "WHERE fonte_codigo = 'tracker' AND ativo = TRUE AND (" + conditions + ") "
        "ORDER BY principal DESC, id LIMIT 1",
        params,
    )
    row = cursor.fetchone()
    return int(row['vehicle_id']) if row else None


def _confirmed_capabilities(cursor, protocol: str) -> Dict[str, Dict]:
    cursor.execute(
        "SELECT i.id, i.capability_code, i.value_type, i.unit "
        "FROM monitoramento.capability_profiles p "
        "JOIN monitoramento.capability_profile_items i ON i.profile_id = p.id "
        "WHERE p.protocol_code = %s AND p.device_model = '*' "
        "AND p.status = 'active' AND i.support_status = 'confirmed' "
        "AND p.version_number = (SELECT MAX(p2.version_number) "
        "FROM monitoramento.capability_profiles p2 "
        "WHERE p2.protocol_code = p.protocol_code "
        "AND p2.device_model = p.device_model AND p2.status = 'active')",
        (protocol,),
    )
    return {row['capability_code']: row for row in cursor.fetchall()}


def _readings_from_packet(data: Dict) -> Iterable[tuple]:
    yield 'position', {
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
    }
    mappings = {
        'speed': 'speed',
        'heading': 'heading',
        'ignition': 'ignition',
        'external_voltage': 'battery_voltage',
        'gps_valid': 'gps_status',
        'altitude': 'altitude',
    }
    for capability, field in mappings.items():
        value = data.get(field)
        if value is not None:
            yield capability, value


def persist_tracker_readings(
    cursor,
    *,
    tracker_vehicle_id: int,
    location_id: int,
    data: Dict,
    received_at: Optional[datetime] = None,
) -> int:
    """Persiste somente campos confirmados; o chamador controla a transação."""
    protocol = str(data.get('protocol') or '').strip().lower()
    if protocol not in {'maxtrack', 'suntech', 'queclink'}:
        raise ValueError(f'Protocolo Tracker não suportado: {protocol or "ausente"}')
    observed_at = _naive_utc(data.get('timestamp'))
    received_at = _naive_utc(received_at or datetime.utcnow())
    if received_at < observed_at:
        received_at = observed_at
    device_id = data.get('device_id')
    external_device_id = str(device_id or f'vehicle:{tracker_vehicle_id}')
    vehicle_id = _resolve_vehicle_id(cursor, tracker_vehicle_id, device_id)
    capabilities = _confirmed_capabilities(cursor, protocol)
    correlation_id = f'tracker:{tracker_vehicle_id}:location:{location_id}'
    inserted = 0

    for capability_code, value in _readings_from_packet(data):
        capability = capabilities.get(capability_code)
        if capability is None:
            continue
        value_type, default_unit = TRACKER_FIELDS[capability_code]
        cursor.execute(
            "INSERT INTO monitoramento.sensors "
            "(vehicle_id, source_code, protocol_code, device_model, "
            "external_device_id, capability_profile_item_id, capability_code, "
            "unit, first_seen_at, last_seen_at) "
            "VALUES (%s, 'tracker', %s, '*', %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE vehicle_id = COALESCE(vehicle_id, VALUES(vehicle_id)), "
            "capability_profile_item_id = VALUES(capability_profile_item_id), "
            "unit = VALUES(unit), lifecycle_status = 'active', "
            "last_seen_at = GREATEST(last_seen_at, VALUES(last_seen_at))",
            (
                vehicle_id, protocol, external_device_id, capability['id'],
                capability_code, capability.get('unit') or default_unit,
                received_at, received_at,
            ),
        )
        cursor.execute(
            "SELECT id FROM monitoramento.sensors WHERE source_code = 'tracker' "
            "AND protocol_code = %s AND external_device_id = %s "
            "AND capability_code = %s",
            (protocol, external_device_id, capability_code),
        )
        sensor_id = int(cursor.fetchone()['id'])
        cursor.execute(
            "INSERT IGNORE INTO monitoramento.sensor_readings "
            "(sensor_id, source_code, value_type, value_json, unit, quality, "
            "observed_at, received_at, correlation_id, source_record_id, metadata_json) "
            "VALUES (%s, 'tracker', %s, %s, %s, 'valid', %s, %s, %s, %s, %s)",
            (
                sensor_id, value_type, json.dumps(value, separators=(',', ':')),
                capability.get('unit') or default_unit, observed_at, received_at,
                correlation_id, str(location_id),
                json.dumps({'protocol': protocol}, separators=(',', ':')),
            ),
        )
        inserted += max(cursor.rowcount, 0)
    return inserted
