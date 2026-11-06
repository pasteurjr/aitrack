import importlib.util
from pathlib import Path
import uuid


BACKFILL_PATH = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / 'backfill_operational_identity.py'
)
SPEC = importlib.util.spec_from_file_location('identity_backfill', BACKFILL_PATH)
backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill)


def test_normalizes_plate_without_formatting_noise():
    assert backfill.normalize_plate(' abc-1d23 ') == 'ABC1D23'
    assert backfill.normalize_plate(None) is None
    assert backfill.normalize_plate('---') is None


def test_public_ids_are_stable_and_entity_scoped():
    first = backfill.stable_public_id('vehicle', 'plate:ABC1D23')
    second = backfill.stable_public_id('vehicle', 'plate:ABC1D23')
    driver = backfill.stable_public_id('driver', 'plate:ABC1D23')

    assert first == second
    assert first != driver
    assert str(uuid.UUID(first)) == first


def test_expected_counts_keep_driver_separate_from_all_historical_vehicles():
    legacy = [
        {'device_id': 'GPS-1', 'placa': 'AAA-0001', 'codusu': None},
        {'device_id': None, 'placa': 'BBB-0002', 'codusu': 7},
    ]
    trips = [
        {'CODUSU': 7, 'placa': 'BBB0002'},
        {'CODUSU': 7, 'placa': 'CCC-0003'},
    ]

    assert backfill.expected_counts(legacy, trips) == {
        'vehicles': 3,
        'drivers': 1,
        'tracker_rows': 1,
        'driver_vehicle_links': 2,
    }


def test_expected_counts_fuses_same_plate_across_sources():
    legacy = [{'device_id': 'GPS-1', 'placa': 'AAA-0001', 'codusu': None}]
    trips = [{'CODUSU': 7, 'placa': 'AAA0001'}]

    assert backfill.expected_counts(legacy, trips)['vehicles'] == 1
