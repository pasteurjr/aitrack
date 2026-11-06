"""Contrato versionado de identidade unificada de veículo.

Este módulo não consulta banco nem altera os endpoints legados. Ele define a
forma canônica que APIs novas devem usar ao representar Tracker e Dirija Bem.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional


SCHEMA_VERSION = "vehicle.v1"


class VehicleIdentityType(str, Enum):
    TRACKER_ONLY = "tracker_only"
    APP_ONLY = "app_only"
    BOTH = "both"


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
class UnifiedVehicleDTO:
    vehicle_id: int
    identity_type: VehicleIdentityType
    display_name: str
    active: bool
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

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "UnifiedVehicleDTO":
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
            "tracker": self.tracker.to_dict() if self.tracker else None,
            "dirijabem": self.dirijabem.to_dict() if self.dirijabem else None,
        }
