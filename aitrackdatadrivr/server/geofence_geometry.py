"""Validação e normalização das geometrias aceitas pela API de cercas."""

import hashlib
import json
import math
from typing import Dict, List, Sequence, Tuple


MAX_CIRCLE_RADIUS_METERS = 100_000.0
MAX_POLYGON_POINTS = 500
Point = Tuple[float, float]


def _number(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{field} deve ser numérico')
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f'{field} deve ser finito')
    return normalized


def _point(value: Sequence, field: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f'{field} deve conter [longitude, latitude]')
    longitude = _number(value[0], f'{field}.longitude')
    latitude = _number(value[1], f'{field}.latitude')
    if not -180 <= longitude <= 180:
        raise ValueError(f'{field}.longitude deve estar entre -180 e 180')
    if not -90 <= latitude <= 90:
        raise ValueError(f'{field}.latitude deve estar entre -90 e 90')
    return longitude, latitude


def _orientation(a: Point, b: Point, c: Point) -> int:
    cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(cross) < 1e-12:
        return 0
    return 1 if cross > 0 else -1


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        min(a[0], b[0]) - 1e-12 <= point[0] <= max(a[0], b[0]) + 1e-12
        and min(a[1], b[1]) - 1e-12 <= point[1] <= max(a[1], b[1]) + 1e-12
    )


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    orientations = (
        _orientation(a, b, c), _orientation(a, b, d),
        _orientation(c, d, a), _orientation(c, d, b),
    )
    if orientations[0] != orientations[1] and orientations[2] != orientations[3]:
        return True
    return any((
        orientations[0] == 0 and _on_segment(a, b, c),
        orientations[1] == 0 and _on_segment(a, b, d),
        orientations[2] == 0 and _on_segment(c, d, a),
        orientations[3] == 0 and _on_segment(c, d, b),
    ))


def _validate_polygon(ring: List[Point]) -> None:
    if len(ring) < 4:
        raise ValueError('Polígono deve estar fechado e ter ao menos três vértices')
    if len(ring) > MAX_POLYGON_POINTS:
        raise ValueError(f'Polígono deve ter no máximo {MAX_POLYGON_POINTS} pontos')
    if ring[0] != ring[-1]:
        raise ValueError('Polígono deve estar fechado: primeiro e último pontos devem ser iguais')
    if any(ring[index] == ring[index + 1] for index in range(len(ring) - 1)):
        raise ValueError('Polígono não pode ter pontos consecutivos iguais')

    edge_count = len(ring) - 1
    for first in range(edge_count):
        for second in range(first + 1, edge_count):
            adjacent = second == first + 1 or (first == 0 and second == edge_count - 1)
            if adjacent:
                continue
            if _segments_intersect(
                ring[first], ring[first + 1], ring[second], ring[second + 1],
            ):
                raise ValueError('Polígono não pode possuir auto-interseções')

    area_twice = sum(
        ring[index][0] * ring[index + 1][1]
        - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    )
    if abs(area_twice) < 1e-12:
        raise ValueError('Polígono deve possuir área')


def _coordinate(value: float) -> str:
    return format(value, '.12g')


def normalize_geometry(geometry: Dict) -> Dict:
    """Retorna geometria canônica, WKT e hash estável para persistência."""
    if not isinstance(geometry, dict):
        raise ValueError('geometry é obrigatório')
    geometry_type = str(geometry.get('type') or '').lower()

    if geometry_type == 'circle':
        center = _point(geometry.get('center'), 'geometry.center')
        radius = _number(geometry.get('radius_meters'), 'geometry.radius_meters')
        if not 0 < radius <= MAX_CIRCLE_RADIUS_METERS:
            raise ValueError(
                f'geometry.radius_meters deve estar entre 0 e {int(MAX_CIRCLE_RADIUS_METERS)}',
            )
        canonical = {
            'type': 'Circle',
            'center': [center[0], center[1]],
            'radius_meters': radius,
        }
        wkt = f'POINT({_coordinate(center[0])} {_coordinate(center[1])})'
        radius_meters = radius
        database_type = 'circle'
    elif geometry_type == 'polygon':
        coordinates = geometry.get('coordinates')
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 1
            or not isinstance(coordinates[0], list)
        ):
            raise ValueError('geometry.coordinates deve conter exatamente um anel externo')
        ring = [_point(point, f'geometry.coordinates[0][{index}]')
                for index, point in enumerate(coordinates[0])]
        _validate_polygon(ring)
        canonical = {
            'type': 'Polygon',
            'coordinates': [[[point[0], point[1]] for point in ring]],
        }
        points = ', '.join(
            f'{_coordinate(point[0])} {_coordinate(point[1])}' for point in ring
        )
        wkt = f'POLYGON(({points}))'
        radius_meters = None
        database_type = 'polygon'
    else:
        raise ValueError('geometry.type deve ser Circle ou Polygon')

    canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
    return {
        'type': database_type,
        'geometry': canonical,
        'wkt': wkt,
        'radius_meters': radius_meters,
        'hash': hashlib.sha256(canonical_json.encode('utf-8')).hexdigest(),
    }
