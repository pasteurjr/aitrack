#!/usr/bin/env python3
"""Replay determinístico de sinais Tracker comprovados, via socket real."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import socket
import time
from typing import Optional

from server.protocol_parsers import parse_data
from simulator import get_maxtrack_packet, get_queclink_packet, get_suntech_packet


BASE_TIME = datetime(2026, 11, 17, 12, 0, 0)
SUPPORTED_PROTOCOLS = {'maxtrack', 'suntech', 'queclink'}
ALLOWED_PARSED_FIELDS = {
    'protocol', 'device_id', 'timestamp', 'gps_status', 'latitude', 'longitude',
    'speed', 'heading', 'ignition', 'battery_voltage', 'panic', 'altitude',
}


@dataclass(frozen=True)
class ScenarioStep:
    name: str
    offset_seconds: int
    speed: float = 40.0
    heading: float = 90.0
    ignition: bool = True
    external_voltage: float = 13.8
    gps_valid: bool = True
    silence_seconds: int = 0


SCENARIOS = {
    'normal': (
        ScenarioStep('normal-1', 0, speed=35.0),
        ScenarioStep('normal-2', 5, speed=42.0, heading=110.0),
        ScenarioStep('normal-3', 10, speed=38.0, heading=125.0),
    ),
    'ignition-cycle': (
        ScenarioStep('ignition-on', 0, speed=15.0, ignition=True),
        ScenarioStep('ignition-off', 5, speed=0.0, ignition=False, external_voltage=12.6),
        ScenarioStep('ignition-restored', 10, speed=10.0, ignition=True),
    ),
    'external-power-loss': (
        ScenarioStep('power-normal', 0, external_voltage=13.8),
        ScenarioStep('power-loss-confirm-1', 5, external_voltage=0.4),
        ScenarioStep('power-loss-confirm-2', 10, external_voltage=0.3),
        ScenarioStep('power-recovery', 15, external_voltage=12.6),
    ),
    'gps-invalid': (
        ScenarioStep('gps-valid', 0, gps_valid=True),
        ScenarioStep('gps-invalid', 5, gps_valid=False),
        ScenarioStep('gps-recovered', 10, gps_valid=True),
    ),
    'offline-silence': (
        ScenarioStep('last-known-position', 0, speed=25.0),
        ScenarioStep('intentional-silence', 5, silence_seconds=70),
        ScenarioStep('telemetry-recovered', 75, speed=20.0),
    ),
}


def scenario_steps(name: str, protocol: str):
    if name not in SCENARIOS:
        raise ValueError(f'Cenário desconhecido: {name}')
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError(f'Protocolo desconhecido: {protocol}')
    if name == 'gps-invalid' and protocol != 'maxtrack':
        raise ValueError('gps-invalid é comprovado somente para Maxtrack')
    return SCENARIOS[name]


def build_packet(protocol: str, device_id: str, step: ScenarioStep,
                 latitude=-23.5505, longitude=-46.6333) -> Optional[bytes]:
    if step.silence_seconds:
        return None
    observed_at = BASE_TIME + timedelta(seconds=step.offset_seconds)
    common = (
        latitude, longitude, step.speed, step.heading, int(step.ignition),
        step.external_voltage,
    )
    if protocol == 'maxtrack':
        packet = get_maxtrack_packet(
            *common, device_id=device_id, observed_at=observed_at,
            gps_valid=step.gps_valid,
        )
    elif protocol == 'suntech':
        packet = get_suntech_packet(device_id, *common, observed_at=observed_at)
    elif protocol == 'queclink':
        packet = get_queclink_packet(
            device_id, *common, altitude=760.0, observed_at=observed_at,
        )
    else:
        raise ValueError(f'Protocolo desconhecido: {protocol}')
    validate_packet(packet, protocol, device_id, step)
    return packet


def validate_packet(packet: bytes, protocol: str, device_id: str, step: ScenarioStep):
    parsed = parse_data(packet)
    if not parsed:
        raise ValueError(f'Parser rejeitou o passo {step.name}')
    unexpected = set(parsed) - ALLOWED_PARSED_FIELDS
    if unexpected:
        raise ValueError(f'Campos não documentados: {sorted(unexpected)}')
    if parsed['protocol'] != protocol or parsed['device_id'] != device_id:
        raise ValueError(f'Identidade divergente no passo {step.name}')
    if parsed['panic'] is not False:
        raise ValueError('Simulador não pode fabricar sinal de pânico')
    if protocol == 'maxtrack' and parsed['gps_status'] != step.gps_valid:
        raise ValueError(f'Estado GPS divergente no passo {step.name}')


def send_packet(packet: bytes, host: str, port: int, timeout=3.0):
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(packet)


def run_scenario(name: str, protocol: str, device_id: str, host: str, port: int,
                 time_scale: float = 1.0, dry_run: bool = False):
    results = []
    previous_offset = 0
    for step in scenario_steps(name, protocol):
        delay = max(0, step.offset_seconds - previous_offset)
        if delay and time_scale:
            time.sleep(delay * time_scale)
        previous_offset = step.offset_seconds
        packet = build_packet(protocol, device_id, step)
        if packet is None:
            if step.silence_seconds and time_scale:
                time.sleep(step.silence_seconds * time_scale)
            results.append({'step': step.name, 'result': 'silence', 'seconds': step.silence_seconds})
            continue
        if not dry_run:
            send_packet(packet, host, port)
        results.append({
            'step': step.name,
            'result': 'validated' if dry_run else 'sent',
            'parsed': parse_data(packet),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=sorted(SCENARIOS))
    parser.add_argument('--protocol', choices=sorted(SUPPORTED_PROTOCOLS), default='suntech')
    parser.add_argument('--device-id', default='SIM-SCENARIO-1')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--time-scale', type=float, default=1.0)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.time_scale < 0:
        parser.error('--time-scale deve ser >= 0')
    try:
        results = run_scenario(
            args.scenario, args.protocol, args.device_id, args.host, args.port,
            args.time_scale, args.dry_run,
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f'falha: {exc}\n')
    print(json.dumps({
        'scenario': args.scenario,
        'protocol': args.protocol,
        'device_id': args.device_id,
        'mode': 'dry-run' if args.dry_run else 'socket',
        'steps': results,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
