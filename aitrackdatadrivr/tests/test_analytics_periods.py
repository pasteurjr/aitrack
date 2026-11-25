from datetime import datetime

import pytest

from server.analytics_db import parse_sources
from server.analytics_periods import comparison_period, parse_period


def test_period_is_semiopen_utc_and_previous_has_equal_duration():
    period = parse_period('2026-11-24T00:00', '2026-11-25T00:00', 'America/Sao_Paulo')
    assert period.start_utc == datetime(2026, 11, 24, 3)
    assert period.end_utc == datetime(2026, 11, 25, 3)
    assert period.public()['interval'] == '[from,to)'
    previous = comparison_period(period, 'previous')
    assert previous.end_utc == period.start_utc
    assert previous.duration_seconds == period.duration_seconds == 86400


def test_custom_comparison_requires_equal_duration():
    period = parse_period('2026-11-24T00:00Z', '2026-11-25T00:00Z', 'UTC')
    with pytest.raises(ValueError, match='mesma duração'):
        comparison_period(period, 'custom', '2026-11-20T00:00Z', '2026-11-20T12:00Z')


def test_period_and_sources_reject_invalid_filters():
    with pytest.raises(ValueError):
        parse_period('2026-11-25', '2026-11-24', 'UTC')
    with pytest.raises(ValueError):
        parse_period('2020-01-01', '2026-01-01', 'UTC')
    with pytest.raises(ValueError):
        parse_sources('tracker,fabricado')
    assert parse_sources('tracker,dirijabem,tracker') == ('tracker', 'dirijabem')
