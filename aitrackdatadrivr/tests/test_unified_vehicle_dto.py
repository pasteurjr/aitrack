import json

import pytest

from server.unified_vehicle_dto import OperationMode, SCHEMA_VERSION, UnifiedVehicleDTO


def test_builds_tracker_only_vehicle_from_existing_record():
    vehicle = UnifiedVehicleDTO.from_record({
        "id": 10,
        "tipo": "tracker_only",
        "device_id": "SIM-1000",
        "veicod": 42,
        "codusu": None,
        "placa": "abc-1d23",
        "descricao": "Veículo de apoio",
        "ativo": 1,
    }, tracker_mode=OperationMode.SIMULATION)

    assert vehicle.to_dict() == {
        "schema_version": SCHEMA_VERSION,
        "vehicle_id": 10,
        "identity_type": "tracker_only",
        "display_name": "Veículo de apoio",
        "plate": "ABC-1D23",
        "active": True,
        "telemetry": [{
            "source": "tracker",
            "mode": "simulation",
            "last_communication_at": None,
        }],
        "tracker": {"device_id": "SIM-1000", "veicod": 42},
        "dirijabem": None,
    }


def test_builds_app_only_vehicle_without_inventing_tracker_identity():
    vehicle = UnifiedVehicleDTO.from_record({
        "id": 20,
        "tipo": "app_only",
        "device_id": None,
        "codusu": 614,
        "placa": None,
        "descricao": "Motorista Dirija Bem",
        "ativo": True,
    })

    assert vehicle.tracker is None
    assert vehicle.to_dict()["dirijabem"] == {"codusu": 614}


def test_builds_both_vehicle_and_is_json_serializable():
    vehicle = UnifiedVehicleDTO.from_record({
        "id": 30,
        "tipo": "both",
        "device_id": "DEV-30",
        "codusu": 30,
        "placa": "XYZ-9Z99",
        "descricao": None,
        "ativo": True,
    })

    payload = vehicle.to_dict()
    assert payload["display_name"] == "XYZ-9Z99"
    assert payload["tracker"] == {"device_id": "DEV-30", "veicod": None}
    assert payload["dirijabem"] == {"codusu": 30}
    assert {item["source"] for item in payload["telemetry"]} == {"tracker", "dirijabem"}
    json.dumps(payload)


def test_exposes_mode_and_last_communication_without_inference():
    vehicle = UnifiedVehicleDTO.from_record({
        "id": 10,
        "tipo": "tracker_only",
        "device_id": "SIM-1000",
        "descricao": "Veículo",
        "tracker_last_communication_at": "2026-11-06T05:30:00-03:00",
    }, tracker_mode=OperationMode.LIVE)

    assert vehicle.to_dict()["telemetry"] == [{
        "source": "tracker",
        "mode": "live",
        "last_communication_at": "2026-11-06T05:30:00-03:00",
    }]


@pytest.mark.parametrize(
    "record",
    [
        {"id": 1, "tipo": "tracker_only", "device_id": None, "codusu": None, "descricao": "Inválido"},
        {"id": 1, "tipo": "app_only", "device_id": "DEV-1", "codusu": 1, "descricao": "Inválido"},
        {"id": 1, "tipo": "both", "device_id": "DEV-1", "codusu": None, "descricao": "Inválido"},
    ],
)
def test_rejects_identity_type_that_disagrees_with_sources(record):
    with pytest.raises(ValueError, match="não corresponde"):
        UnifiedVehicleDTO.from_record(record)


def test_rejects_unknown_identity_type():
    with pytest.raises(ValueError):
        UnifiedVehicleDTO.from_record({"id": 1, "tipo": "desconhecido"})
