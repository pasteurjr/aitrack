from server.protocol_parsers import parse_data


def test_parse_maxtrack_with_prefix_device_id():
    did = "SIM-1234"
    pkt = ">REV01;010125;120102;A;-23.55050;-46.63330;30.0;90;1;12.5;0;3<"
    raw = f"{did}|{pkt}".encode("ascii")
    parsed = parse_data(raw)
    assert parsed is not None
    assert parsed["protocol"] == "maxtrack"
    assert parsed["device_id"] == did
    assert abs(parsed["latitude"] + 23.55050) < 1e-6
    assert abs(parsed["longitude"] + 46.63330) < 1e-6


def test_parse_suntech():
    raw = (
        "ST310U;SIM-2000;01;20250101;120102;-23.55050;-46.63330;30.0;90.0;1;1;12.5;3.7;0;1;BR;724;31;1234;5678"
    ).encode("ascii")
    parsed = parse_data(raw)
    assert parsed is not None
    assert parsed["protocol"] == "suntech"
    assert parsed["device_id"] == "SIM-2000"
