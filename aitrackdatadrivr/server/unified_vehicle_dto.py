"""Contrato versionado de identidade unificada de veículo.

Este módulo não consulta banco nem altera os endpoints legados. Ele define a
forma canônica que APIs novas devem usar ao representar Tracker e Dirija Bem.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Mapping, Optional


SCHEMA_VERSION = "vehicle.v1"


class VehicleIdentityType(str, Enum):
    TRACKER_ONLY = "tracker_only"
    APP_ONLY = "app_only"
    BOTH = "both"


class TelemetrySource(str, Enum):
    TRACKER = "tracker"
    DIRIJABEM = "dirijabem"


class OperationMode(str, Enum):
    LIVE = "live"
    SIMULATION = "simulation"
    REPLAY = "replay"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


@dataclass(frozen=True)
class TrackerIdentityDTO:
    device_id: str
    veicod: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError("tracker.device_id é obrigatório")
        if self.veicod is not None and self.veicod <= 0:
            raise ValueError("tracker.veicod deve ser positivo")

    def to_dict(self) -> Dict[str, Any]:
        return {"device_id": self.device_id, "veicod": self.veicod}


@dataclass(frozen=True)
class DirijabemIdentityDTO:
    codusu: int

    def __post_init__(self) -> None:
        if self.codusu <= 0:
            raise ValueError("dirijabem.codusu deve ser positivo")

    def to_dict(self) -> Dict[str, int]:
        return {"codusu": self.codusu}


@dataclass(frozen=True)
class TelemetryProvenanceDTO:
    source: TelemetrySource
    mode: OperationMode
    last_communication_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.last_communication_at is not None:
            try:
                datetime.fromisoformat(self.last_communication_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("last_communication_at deve usar formato ISO 8601") from exc

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "source": self.source.value,
            "mode": self.mode.value,
            "last_communication_at": self.last_communication_at,
        }


@dataclass(frozen=True)
class UnifiedVehicleDTO:
    vehicle_id: int
    identity_type: VehicleIdentityType
    display_name: str
    active: bool
    telemetry: tuple[TelemetryProvenanceDTO, ...]
    plate: Optional[str] = None
    tracker: Optional[TrackerIdentityDTO] = None
    dirijabem: Optional[DirijabemIdentityDTO] = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.vehicle_id <= 0:
            raise ValueError("vehicle_id deve ser positivo")
        if not self.display_name.strip():
            raise ValueError("display_name é obrigatório")
        if not isinstance(self.active, bool):
            raise ValueError("active deve ser booleano")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version deve ser {SCHEMA_VERSION}")

        has_tracker = self.tracker is not None
        has_dirijabem = self.dirijabem is not None
        expected_sources = {
            VehicleIdentityType.TRACKER_ONLY: (True, False),
            VehicleIdentityType.APP_ONLY: (False, True),
            VehicleIdentityType.BOTH: (True, True),
        }
        if (has_tracker, has_dirijabem) != expected_sources[self.identity_type]:
            raise ValueError(
                f"identity_type={self.identity_type.value} não corresponde às identidades fornecidas"
            )

        expected_telemetry_sources = set()
        if has_tracker:
            expected_telemetry_sources.add(TelemetrySource.TRACKER)
        if has_dirijabem:
            expected_telemetry_sources.add(TelemetrySource.DIRIJABEM)
        actual_telemetry_sources = {item.source for item in self.telemetry}
        if len(actual_telemetry_sources) != len(self.telemetry):
            raise ValueError("telemetry não pode repetir uma fonte")
        if actual_telemetry_sources != expected_telemetry_sources:
            raise ValueError("telemetry deve representar exatamente as identidades disponíveis")

    @classmethod
    def from_record(
        cls,
        record: Mapping[str, Any],
        tracker_mode: OperationMode = OperationMode.UNKNOWN,
        dirijabem_mode: OperationMode = OperationMode.UNKNOWN,
    ) -> "UnifiedVehicleDTO":
        """Converte uma linha da tabela ``veiculo_unificado`` para o DTO v1."""
        identity_type = VehicleIdentityType(record["tipo"])
        device_id = _optional_text(record.get("device_id"))
        codusu = _optional_int(record.get("codusu"))
        veicod = _optional_int(record.get("veicod"))
        plate = _optional_text(record.get("placa"))
        if plate:
            plate = plate.upper()

        tracker = TrackerIdentityDTO(device_id=device_id, veicod=veicod) if device_id else None
        dirijabem = DirijabemIdentityDTO(codusu=codusu) if codusu is not None else None
        telemetry = []
        if tracker:
            telemetry.append(TelemetryProvenanceDTO(
                source=TelemetrySource.TRACKER,
                mode=tracker_mode,
                last_communication_at=_iso_datetime(record.get("tracker_last_communication_at")),
            ))
        if dirijabem:
            telemetry.append(TelemetryProvenanceDTO(
                source=TelemetrySource.DIRIJABEM,
                mode=dirijabem_mode,
                last_communication_at=_iso_datetime(record.get("dirijabem_last_communication_at")),
            ))
        display_name = (
            _optional_text(record.get("descricao"))
            or plate
            or device_id
            or (f"Dirija Bem {codusu}" if codusu is not None else None)
        )
        if display_name is None:
            raise ValueError("registro não possui descrição nem identidade exibível")

        return cls(
            vehicle_id=int(record["id"]),
            identity_type=identity_type,
            display_name=display_name,
            plate=plate,
            active=bool(record.get("ativo", True)),
            telemetry=tuple(telemetry),
            tracker=tracker,
            dirijabem=dirijabem,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "vehicle_id": self.vehicle_id,
            "identity_type": self.identity_type.value,
            "display_name": self.display_name,
            "plate": self.plate,
            "active": self.active,
            "telemetry": [item.to_dict() for item in self.telemetry],
            "tracker": self.tracker.to_dict() if self.tracker else None,
            "dirijabem": self.dirijabem.to_dict() if self.dirijabem else None,
        }


def _iso_datetime(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    normalized = str(value).strip()
    datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return normalized
