import importlib.util
from pathlib import Path


BACKFILL_PATH = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / 'backfill_operational_incidents.py'
)
SPEC = importlib.util.spec_from_file_location('incident_backfill', BACKFILL_PATH)
backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill)


def test_plate_normalization_matches_identity_backfill():
    assert backfill.normalize_plate(' abc-1d23 ') == 'ABC1D23'
    assert backfill.normalize_plate(None) is None


def test_incident_copy_lists_all_outcome_and_sla_columns():
    for column in (
        'sla_due_at', 'detection_outcome', 'classification_reason',
        'classified_by', 'classified_at', 'version', 'created_at', 'updated_at',
    ):
        assert column in backfill.INCIDENT_COLUMNS


def test_timeline_copy_preserves_audit_and_causality_columns():
    for column in (
        'idempotency_key', 'actor_type', 'correlation_id', 'causation_id',
        'visibility', 'occurred_at', 'recorded_at',
    ):
        assert column in backfill.TIMELINE_COLUMNS
