import socket
from threading import Thread

import pytest

from tracker_scenario_simulator import (
    ALLOWED_PARSED_FIELDS,
    SCENARIOS,
    build_packet,
    run_scenario,
    scenario_steps,
)
from server.protocol_parsers import parse_data


@pytest.mark.parametrize('protocol', ['maxtrack', 'suntech', 'queclink'])
@pytest.mark.parametrize('scenario', ['normal', 'ignition-cycle', 'external-power-loss', 'offline-silence'])
def test_scenarios_are_deterministic_and_only_emit_supported_fields(protocol, scenario):
    for step in scenario_steps(scenario, protocol):
        first = build_packet(protocol, 'SIM-DETERMINISTIC', step)
        second = build_packet(protocol, 'SIM-DETERMINISTIC', step)
        assert first == second
        if first is None:
            assert step.silence_seconds > 0
            continue
        parsed = parse_data(first)
        assert set(parsed) <= ALLOWED_PARSED_FIELDS
        assert parsed['panic'] is False
        assert parsed['device_id'] == 'SIM-DETERMINISTIC'


def test_gps_failure_is_limited_to_protocol_that_really_exposes_status():
    steps = scenario_steps('gps-invalid', 'maxtrack')
    assert [parse_data(build_packet('maxtrack', 'SIM-GPS', step))['gps_status'] for step in steps] == [
        True, False, True,
    ]
    with pytest.raises(ValueError, match='somente para Maxtrack'):
        scenario_steps('gps-invalid', 'suntech')


def test_power_scenario_has_confirmed_loss_and_recovery_sequence():
    values = [step.external_voltage for step in SCENARIOS['external-power-loss']]
    assert values == [13.8, 0.4, 0.3, 12.6]


def test_socket_mode_sends_validated_packets_to_real_tcp_listener():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    port = listener.getsockname()[1]
    received = []

    def receive_three():
        for _ in range(3):
            connection, _address = listener.accept()
            with connection:
                received.append(connection.recv(4096))
        listener.close()

    thread = Thread(target=receive_three)
    thread.start()
    results = run_scenario(
        'normal', 'suntech', 'SIM-SOCKET', '127.0.0.1', port, time_scale=0,
    )
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert len(received) == 3
    assert all(parse_data(packet)['device_id'] == 'SIM-SOCKET' for packet in received)
    assert [item['result'] for item in results] == ['sent', 'sent', 'sent']


def test_dry_run_offline_records_silence_without_opening_socket():
    results = run_scenario(
        'offline-silence', 'queclink', 'SIM-OFFLINE', 'invalid', 1,
        time_scale=0, dry_run=True,
    )
    assert [item['result'] for item in results] == ['validated', 'silence', 'validated']
    assert results[1]['seconds'] == 70
