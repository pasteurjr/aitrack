"""Cenários determinísticos para provar o motor operacional de cercas."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from typing import Callable, Dict, List, Sequence, Tuple


Point = Tuple[float, float]


@dataclass(frozen=True)
class ReplayPoint:
    label: str
    offset_seconds: int
    longitude: float
    latitude: float


@dataclass(frozen=True)
class ExpectedEvent:
    point_label: str
    event_type: str
    crossing_direction: str | None


@dataclass(frozen=True)
class ReplayScenario:
    name: str
    start_at: datetime
    geometry: Dict
    rule: str
    schedules: Sequence[Dict]
    points: Sequence[ReplayPoint]
    expected_events: Sequence[ExpectedEvent]
    dwell_threshold_seconds: int = 2
    hysteresis_meters: float = 30.0
    confirmation_samples: int = 2


class ReplayMismatch(AssertionError):
    pass


def _meters_east(center: Point, meters: float) -> Point:
    longitude, latitude = center
    longitude_degrees = meters / (111_320.0 * math.cos(math.radians(latitude)))
    return longitude + longitude_degrees, latitude


def standard_scenarios() -> Tuple[ReplayScenario, ...]:
    """Retorna sempre os mesmos pontos, horários e resultados esperados."""
    center = (-46.6333, -23.5505)
    circle_start = datetime(2026, 11, 9, 10, 0, 0)
    circle = {'type': 'Circle', 'center': list(center), 'radius_meters': 300.0}
    circle_neutral_outside = _meters_east(center, 310.0)
    circle_neutral_inside = _meters_east(center, 290.0)
    circle_outside = _meters_east(center, 420.0)

    polygon_half_width = 300.0
    west = _meters_east(center, -polygon_half_width)[0]
    east = _meters_east(center, polygon_half_width)[0]
    south = center[1] - polygon_half_width / 111_320.0
    north = center[1] + polygon_half_width / 111_320.0
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [west, south], [east, south], [east, north], [west, north],
            [west, south],
        ]],
    }
    polygon_outside = _meters_east(center, 450.0)
    polygon_neutral_outside = _meters_east(center, 310.0)
    polygon_neutral_inside = _meters_east(center, 290.0)
    polygon_start = datetime(2026, 11, 9, 11, 0, 0)

    schedule_start = datetime(2026, 11, 9, 7, 59, 50)
    return (
        ReplayScenario(
            name='circle_allowed',
            start_at=circle_start,
            geometry=circle,
            rule='allowed',
            schedules=(),
            points=(
                ReplayPoint('baseline_inside', 0, *center),
                ReplayPoint('neutral_outside', 1, *circle_neutral_outside),
                ReplayPoint('outside_confirmation_1', 2, *circle_outside),
                ReplayPoint('outside_confirmation_2', 3, *circle_outside),
                ReplayPoint('dwell_due', 5, *circle_outside),
                ReplayPoint('neutral_inside', 6, *circle_neutral_inside),
                ReplayPoint('inside_confirmation_1', 7, *center),
                ReplayPoint('inside_confirmation_2', 8, *center),
            ),
            expected_events=(
                ExpectedEvent('outside_confirmation_2', 'geofence_exit', 'inside_to_outside'),
                ExpectedEvent('dwell_due', 'geofence_dwell', None),
                ExpectedEvent('inside_confirmation_2', 'geofence_entry', 'outside_to_inside'),
            ),
        ),
        ReplayScenario(
            name='polygon_forbidden',
            start_at=polygon_start,
            geometry=polygon,
            rule='forbidden',
            schedules=(),
            points=(
                ReplayPoint('baseline_outside', 0, *polygon_outside),
                ReplayPoint('neutral_outside', 1, *polygon_neutral_outside),
                ReplayPoint('inside_confirmation_1', 2, *center),
                ReplayPoint('inside_confirmation_2', 3, *center),
                ReplayPoint('dwell_due', 5, *center),
                ReplayPoint('neutral_inside', 6, *polygon_neutral_inside),
                ReplayPoint('outside_confirmation_1', 7, *polygon_outside),
                ReplayPoint('outside_confirmation_2', 8, *polygon_outside),
            ),
            expected_events=(
                ExpectedEvent('inside_confirmation_2', 'geofence_entry', 'outside_to_inside'),
                ExpectedEvent('dwell_due', 'geofence_dwell', None),
                ExpectedEvent('outside_confirmation_2', 'geofence_exit', 'inside_to_outside'),
            ),
        ),
        ReplayScenario(
            name='scheduled_forbidden_circle',
            start_at=schedule_start,
            geometry=circle,
            rule='forbidden',
            schedules=({
                'day_of_week': 0,
                'start_time': '08:00:00',
                'end_time': '09:00:00',
                'crosses_midnight': False,
            },),
            points=(
                ReplayPoint('baseline_outside_before_schedule', 0, *circle_outside),
                ReplayPoint('inside_before_schedule_1', 1, *center),
                ReplayPoint('inside_before_schedule_2', 2, *center),
                ReplayPoint('schedule_started', 10, *center),
                ReplayPoint('dwell_due', 12, *center),
                ReplayPoint('outside_confirmation_1', 13, *circle_outside),
                ReplayPoint('outside_confirmation_2', 14, *circle_outside),
            ),
            expected_events=(
                ExpectedEvent('dwell_due', 'geofence_dwell', None),
                ExpectedEvent('outside_confirmation_2', 'geofence_exit', 'inside_to_outside'),
            ),
        ),
    )


def execute_replay(
    scenario: ReplayScenario,
    evaluator: Callable[..., List[Dict]],
    external_prefix: str,
) -> List[Dict]:
    """Emite a sequência em relógio fixo e anexa o rótulo que causou o evento."""
    events = []
    for index, point in enumerate(scenario.points):
        timestamp = scenario.start_at + timedelta(seconds=point.offset_seconds)
        emitted = evaluator(
            longitude=point.longitude,
            latitude=point.latitude,
            observed_at=timestamp,
            received_at=timestamp,
            accuracy_m=0.0,
            external_position_id=f'{external_prefix}:{scenario.name}:{index}',
        )
        events.extend({'point_label': point.label, **event} for event in emitted)
    return events


def validate_replay(scenario: ReplayScenario, events: Sequence[Dict]) -> None:
    """Falha com diagnóstico legível se tipo, direção ou episódio divergirem."""
    actual = [
        (item['point_label'], item['event_type'], item['crossing_direction'])
        for item in events
    ]
    expected = [
        (item.point_label, item.event_type, item.crossing_direction)
        for item in scenario.expected_events
    ]
    if actual != expected:
        raise ReplayMismatch(
            f'{scenario.name}: eventos divergentes; esperado={expected!r}; obtido={actual!r}'
        )
    incident_ids = {item.get('incident_id') for item in events}
    if None in incident_ids or len(incident_ids) != 1:
        raise ReplayMismatch(
            f'{scenario.name}: eventos não convergiram para um incidente: {incident_ids!r}'
        )
