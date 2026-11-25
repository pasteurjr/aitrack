"""Normalização de períodos analíticos em intervalos UTC semiabertos."""

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MAX_PERIOD_SECONDS = 366 * 24 * 60 * 60


@dataclass(frozen=True)
class AnalyticsPeriod:
    start_utc: datetime
    end_utc: datetime
    timezone_name: str

    @property
    def duration_seconds(self):
        return int((self.end_utc - self.start_utc).total_seconds())

    def previous(self):
        duration = self.end_utc - self.start_utc
        return AnalyticsPeriod(self.start_utc - duration, self.start_utc, self.timezone_name)

    def public(self):
        utc = timezone.utc
        return {
            'from': self.start_utc.replace(tzinfo=utc).isoformat(),
            'to': self.end_utc.replace(tzinfo=utc).isoformat(),
            'timezone': self.timezone_name,
            'duration_seconds': self.duration_seconds,
            'interval': '[from,to)',
        }


def parse_period(start, end, timezone_name='America/Sao_Paulo'):
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('timezone inválido') from exc

    def parse(value, field):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{field} é obrigatório')
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError(f'{field} inválido') from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=zone)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    start_utc = parse(start, 'from')
    end_utc = parse(end, 'to')
    duration = (end_utc - start_utc).total_seconds()
    if duration <= 0 or duration > MAX_PERIOD_SECONDS:
        raise ValueError('período deve ser positivo e ter no máximo 366 dias')
    return AnalyticsPeriod(start_utc, end_utc, timezone_name)


def comparison_period(primary, mode='previous', custom_from=None, custom_to=None):
    if mode in (None, '', 'none'):
        return None
    if mode == 'previous':
        return primary.previous()
    if mode != 'custom':
        raise ValueError('comparison deve ser none, previous ou custom')
    custom = parse_period(custom_from, custom_to, primary.timezone_name)
    if custom.duration_seconds != primary.duration_seconds:
        raise ValueError('períodos comparados devem ter a mesma duração')
    return custom
