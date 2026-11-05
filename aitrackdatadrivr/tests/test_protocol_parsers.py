from server.protocol_parsers import parse_data


def test_maxtrack_maps_available_fields_with_explicit_device_prefix():
    packet = (
        "SIM-MAX-1|>REV01;051126;120102;A;-23.55050;-46.63330;"
        "30.0;90;1;12.5;0;3<"
    ).encode("ascii")

    parsed = parse_data(packet)

    assert parsed == {
        "protocol": "maxtrack",
        "device_id": "SIM-MAX-1",
        "timestamp": "2026-11-05T12:01:02",
        "gps_status": True,
        "latitude": -23.5505,
        "longitude": -46.6333,
        "speed": 30.0,
        "heading": 90,
        "ignition": True,
        "battery_voltage": 12.5,
        "panic": False,
        "altitude": None,
    }


def test_suntech_maps_simulator_packet_fields():
    packet = (
        "ST310U;SIM-SUN-1;01;20261105;12:01:02;-23.55050;-46.63330;"
        "30.0;90.0;1;1;12.5;3.7;0;1;BR;724;31;1234;5678"
    ).encode("ascii")

    parsed = parse_data(packet)

    assert parsed is not None
    assert parsed["protocol"] == "suntech"
    assert parsed["device_id"] == "SIM-SUN-1"
    assert parsed["timestamp"] == "2026-11-05T12:01:02"
    assert parsed["ignition"] is True
    assert parsed["battery_voltage"] == 12.5
    assert parsed["altitude"] is None


def test_queclink_maps_simulator_packet_fields():
    packet = (
        "+RESP:GTRIC,SIM-QUE-1,1,1,0,7,051126,120102,-23.55050,-46.63330,"
        "30.0,90,1,100,12.5,98765,1234,5678,724,31,1,800.0\r\n"
    ).encode("ascii")

    parsed = parse_data(packet)

    assert parsed is not None
    assert parsed["protocol"] == "queclink"
    assert parsed["device_id"] == "SIM-QUE-1"
    assert parsed["timestamp"] == "2026-11-05T12:01:02"
    assert parsed["gps_status"] is True
    assert parsed["latitude"] == -23.5505
    assert parsed["longitude"] == -46.6333
    assert parsed["speed"] == 30.0
    assert parsed["heading"] == 90.0
    assert parsed["ignition"] is True
    assert parsed["battery_voltage"] == 12.5
    assert parsed["altitude"] == 800.0


def test_unknown_packet_is_rejected():
    assert parse_data(b"UNKNOWN;payload") is None
