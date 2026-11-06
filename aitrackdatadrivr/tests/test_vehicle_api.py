from flask import Flask

from server import vehicle_api


def _client():
    app = Flask(__name__)
    app.register_blueprint(vehicle_api.vehicle_bp)
    return app.test_client()


def test_lists_versioned_vehicles_with_explicit_provenance(monkeypatch):
    monkeypatch.setenv("AITRACK_TRACKER_MODE", "simulation")
    monkeypatch.setenv("AITRACK_DIRIJABEM_MODE", "replay")
    monkeypatch.setattr(
        vehicle_api.monitor_db,
        "get_all_unified_vehicles",
        lambda: [{
            "id": 1,
            "tipo": "both",
            "device_id": "SIM-1000",
            "codusu": 614,
            "placa": "ABC-1D23",
            "descricao": "Veículo integrado",
            "ativo": True,
            "tracker_last_communication_at": "2026-11-06T05:30:00",
            "dirijabem_last_communication_at": None,
        }],
    )

    response = _client().get("/api/v1/vehicles")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == "vehicle.v1"
    assert payload["total"] == 1
    assert payload["vehicles"][0]["telemetry"] == [
        {
            "source": "tracker",
            "mode": "simulation",
            "last_communication_at": "2026-11-06T05:30:00",
        },
        {
            "source": "dirijabem",
            "mode": "replay",
            "last_communication_at": None,
        },
    ]


def test_invalid_configured_mode_falls_back_to_unknown(monkeypatch):
    monkeypatch.setenv("AITRACK_TRACKER_MODE", "invalido")
    monkeypatch.setattr(
        vehicle_api.monitor_db,
        "get_all_unified_vehicles",
        lambda: [{
            "id": 1,
            "tipo": "tracker_only",
            "device_id": "SIM-1000",
            "codusu": None,
            "descricao": "Veículo",
            "ativo": True,
        }],
    )

    response = _client().get("/api/v1/vehicles")

    assert response.status_code == 200
    assert response.get_json()["vehicles"][0]["telemetry"][0]["mode"] == "unknown"
