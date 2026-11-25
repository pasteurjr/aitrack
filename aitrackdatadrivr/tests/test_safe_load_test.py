import pytest

from scripts.run_safe_load_test import assert_local_target, percentile, run


def test_load_harness_refuses_shared_or_remote_targets():
    assert_local_target('http://127.0.0.1:5009')
    assert_local_target('http://localhost:5009')
    with pytest.raises(ValueError, match='loopback'):
        assert_local_target('http://192.168.0.100:8085')
    with pytest.raises(ValueError, match='loopback'):
        assert_local_target('https://production.example')


def test_percentile_is_stable_at_boundaries():
    assert percentile([], .95) == 0
    assert percentile([1, 2, 3, 4, 5], .0) == 1
    assert percentile([1, 2, 3, 4, 5], 1.0) == 5


def test_isolated_load_replay_and_restart_have_no_loss_or_duplicate():
    result = run(iterations=200, workers=2)
    assert result['passed'] is True
    assert result['environment'] == 'isolated-temporary-sqlite'
    assert result['before_restart'] == result['after_restart']
    assert set(result['duplicate_counts'].values()) == {0}
    assert result['rpo_records_lost'] == 0
    assert result['recovered_expired_leases'] == 100
