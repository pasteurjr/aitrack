"""Persistência tipada e idempotente de sensores e leituras operacionais."""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional
from zoneinfo import ZoneInfo

from .monitor_db import get_connection


TRACKER_FIELDS = {
    'position': ('geo', None),
    'speed': ('number', 'km/h'),
    'heading': ('number', 'degree'),
    'ignition': ('boolean', None),
    'external_voltage': ('number', 'V'),
    'gps_valid': ('boolean', None),
    'altitude': ('number', 'm'),
}
SENSOR_STALE_AFTER_SECONDS = 120
SERVER_TIMEZONE = ZoneInfo(os.getenv('AITRACK_TIMEZONE', 'America/Sao_Paulo'))


def _naive_utc(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime):
        raise ValueError('observed_at deve ser datetime ou ISO-8601')
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _iso_datetime(value, *, server_time: bool = False):
    if not isinstance(value, datetime):
        return value
    if server_time and value.tzinfo is None:
        value = value.replace(tzinfo=SERVER_TIMEZONE)
    return value.isoformat()


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
            "last_seen_at = VALUES(last_seen_at)",
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


def get_vehicle_sensors(vehicle_id: int) -> Optional[Dict]:
    """Lista somente sensores comprovados/observados do veículo operacional."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, public_id, placa, ativo FROM monitoramento.veiculos "
            "WHERE id = %s AND merged_into_id IS NULL",
            (vehicle_id,),
        )
        vehicle = cursor.fetchone()
        if not vehicle:
            return None
        cursor.execute(
            "SELECT s.id, s.source_code, s.protocol_code, s.device_model, "
            "s.external_device_id, s.capability_code, s.unit, s.lifecycle_status, "
            "s.first_seen_at, s.last_seen_at, i.support_status, i.evidence, "
            "r.value_type, r.value_json, r.unit AS reading_unit, r.quality, "
            "r.observed_at, r.received_at, r.created_at AS recorded_at, "
            "GREATEST(TIMESTAMPDIFF(SECOND, r.created_at, CURRENT_TIMESTAMP(6)), 0) "
            "AS age_seconds, "
            "TIMESTAMPDIFF(SECOND, r.received_at, r.observed_at) AS clock_skew_seconds "
            "FROM monitoramento.sensors s "
            "LEFT JOIN monitoramento.capability_profile_items i "
            "ON i.id = s.capability_profile_item_id "
            "LEFT JOIN monitoramento.sensor_readings r ON r.id = ("
            "SELECT r2.id FROM monitoramento.sensor_readings r2 "
            "WHERE r2.sensor_id = s.id ORDER BY r2.created_at DESC, r2.id DESC LIMIT 1) "
            "WHERE s.vehicle_id = %s "
            "ORDER BY s.source_code, s.protocol_code, s.capability_code",
            (vehicle_id,),
        )
        sensors = cursor.fetchall()
        for sensor in sensors:
            for field in ('first_seen_at', 'last_seen_at', 'received_at', 'recorded_at'):
                sensor[field] = _iso_datetime(sensor.get(field), server_time=True)
            sensor['observed_at'] = _iso_datetime(sensor.get('observed_at'))
            sensor['configured'] = True
            sensor['support_status'] = sensor['support_status'] or 'unknown'
            value_json = sensor.pop('value_json', None)
            if value_json is None:
                sensor['health_status'] = 'unavailable'
                sensor['latest_reading'] = None
            else:
                age_seconds = int(sensor.pop('age_seconds') or 0)
                quality = sensor.pop('quality') or 'unknown'
                if quality == 'invalid':
                    health_status = 'invalid'
                elif age_seconds > SENSOR_STALE_AFTER_SECONDS:
                    health_status = 'stale'
                else:
                    health_status = 'current'
                sensor['health_status'] = health_status
                sensor['latest_reading'] = {
                    'value': json.loads(value_json),
                    'value_type': sensor.pop('value_type'),
                    'unit': sensor.pop('reading_unit') or sensor.get('unit'),
                    'quality': quality,
                    'observed_at': sensor.pop('observed_at'),
                    'received_at': sensor.pop('received_at'),
                    'recorded_at': sensor.pop('recorded_at'),
                    'age_seconds': age_seconds,
                    'clock_skew_seconds': sensor.pop('clock_skew_seconds'),
                    'observed_timezone': 'unspecified',
                    'received_timezone': str(SERVER_TIMEZONE),
                }
            for transient in (
                'value_type', 'reading_unit', 'quality', 'observed_at',
                'received_at', 'recorded_at', 'age_seconds', 'clock_skew_seconds',
            ):
                sensor.pop(transient, None)
        protocols = sorted({sensor['protocol_code'] for sensor in sensors})
        sources = sorted({sensor['source_code'] for sensor in sensors})
        commands = []
        if protocols:
            placeholders = ','.join(['%s'] * len(protocols))
            cursor.execute(
                "SELECT p.protocol_code, i.capability_code, i.support_status, i.evidence "
                "FROM monitoramento.capability_profiles p "
                "JOIN monitoramento.capability_profile_items i ON i.profile_id = p.id "
                f"WHERE p.protocol_code IN ({placeholders}) AND p.device_model='*' "
                "AND p.status='active' AND i.capability_type='command' "
                "AND p.version_number=(SELECT MAX(p2.version_number) "
                "FROM monitoramento.capability_profiles p2 "
                "WHERE p2.protocol_code=p.protocol_code AND p2.device_model=p.device_model "
                "AND p2.status='active') "
                "ORDER BY p.protocol_code, i.capability_code",
                protocols,
            )
            commands = cursor.fetchall()
        return {
            'schema_version': 'vehicle-sensors.v1',
            'vehicle': {
                'id': int(vehicle['id']),
                'public_id': vehicle['public_id'],
                'plate': vehicle['placa'],
                'active': bool(vehicle['ativo']),
            },
            'sources': sources,
            'protocols': protocols,
            'commands': commands,
            'confirmed_commands': [
                command for command in commands
                if command['support_status'] == 'confirmed'
            ],
            'count': len(sensors),
            'sensors': sensors,
        }
    finally:
        cursor.close()
        connection.close()
