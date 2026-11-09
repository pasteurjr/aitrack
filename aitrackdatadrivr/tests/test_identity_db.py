import pytest

from server import identity_db


LEGACY = [{'id': 1, 'placa': 'AAA-0001'}]
OPERATIONAL = [
    {'id': 7, 'placa': 'AAA0001'},
    {'id': 8, 'placa': 'BBB0002'},
]


def test_shadow_reads_both_models_and_preserves_legacy_contract():
    calls = []

    result = identity_db.get_unified_vehicle_records(
        mode='shadow',
        legacy_loader=lambda: calls.append('legacy') or LEGACY,
        operational_loader=lambda: calls.append('operational') or OPERATIONAL,
    )

    assert result == LEGACY
    assert calls == ['operational', 'legacy']


def test_operational_mode_returns_new_read_model():
    result = identity_db.get_unified_vehicle_records(
        mode='operational',
        legacy_loader=lambda: (_ for _ in ()).throw(AssertionError('sem legado')),
        operational_loader=lambda: OPERATIONAL,
    )

    assert result == OPERATIONAL


def test_operational_failure_has_controlled_fallback(monkeypatch):
    monkeypatch.setenv('AITRACK_IDENTITY_ALLOW_FALLBACK', '1')

    result = identity_db.get_unified_vehicle_records(
        mode='operational',
        legacy_loader=lambda: LEGACY,
        operational_loader=lambda: (_ for _ in ()).throw(RuntimeError('offline')),
    )

    assert result == LEGACY


def test_operational_failure_can_be_configured_to_fail_closed(monkeypatch):
    monkeypatch.setenv('AITRACK_IDENTITY_ALLOW_FALLBACK', '0')

    with pytest.raises(RuntimeError, match='offline'):
        identity_db.get_unified_vehicle_records(
            mode='operational',
            legacy_loader=lambda: LEGACY,
            operational_loader=lambda: (_ for _ in ()).throw(RuntimeError('offline')),
        )


def test_comparison_exposes_coverage_gap_without_equating_ids():
    comparison = identity_db.compare_read_models(LEGACY, OPERATIONAL)

    assert comparison == {
        'legacy_total': 1,
        'operational_total': 2,
        'common_plates': 1,
        'only_legacy': 0,
        'only_operational': 1,
    }


def test_invalid_explicit_mode_is_rejected():
    with pytest.raises(ValueError, match='Modo de identidade inválido'):
        identity_db.get_unified_vehicle_records(mode='silencioso')


def test_operational_is_default_and_fallback_is_opt_in(monkeypatch):
    monkeypatch.delenv('AITRACK_IDENTITY_READ_MODEL', raising=False)
    monkeypatch.delenv('AITRACK_IDENTITY_ALLOW_FALLBACK', raising=False)

    assert identity_db.configured_read_mode() == 'operational'
    with pytest.raises(RuntimeError, match='offline'):
        identity_db.get_unified_vehicle_records(
            legacy_loader=lambda: LEGACY,
            operational_loader=lambda: (_ for _ in ()).throw(RuntimeError('offline')),
        )
