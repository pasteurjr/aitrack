"""Cálculo puro e versionado de exposição de condução."""

import math


FORMULA_VERSION = 'exposure-v1'
MAX_SEGMENT_SECONDS = 300
MAX_SPEED_KMH = 220
DRIVING_SPEED_KMH = 3


def haversine_km(first, second):
    lat1, lon1 = math.radians(first['latitude']), math.radians(first['longitude'])
    lat2, lon2 = math.radians(second['latitude']), math.radians(second['longitude'])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def calculate_exposure(points):
    """Descarta segmentos fora de ordem, lacunas e velocidades fisicamente inválidas."""
    distance_km = 0.0
    driving_seconds = 0
    valid_segments = 0
    discarded_segments = 0
    ordered = list(points)
    for previous, current in zip(ordered, ordered[1:]):
        elapsed = (current['observed_at'] - previous['observed_at']).total_seconds()
        if elapsed <= 0 or elapsed > MAX_SEGMENT_SECONDS:
            discarded_segments += 1
            continue
        segment_km = haversine_km(previous, current)
        inferred_speed = segment_km / (elapsed / 3600)
        if inferred_speed > MAX_SPEED_KMH:
            discarded_segments += 1
            continue
        valid_segments += 1
        distance_km += segment_km
        average_speed = (float(previous.get('speed_kmh') or 0) + float(current.get('speed_kmh') or 0)) / 2
        if average_speed >= DRIVING_SPEED_KMH:
            driving_seconds += int(elapsed)
    total_segments = valid_segments + discarded_segments
    return {
        'formula_version': FORMULA_VERSION,
        'distance_km': round(distance_km, 6),
        'driving_seconds': driving_seconds,
        'valid_segments': valid_segments,
        'discarded_segments': discarded_segments,
        'coverage': valid_segments / total_segments if total_segments else 0.0,
        'quality': 'unavailable' if not total_segments else 'complete' if not discarded_segments else 'partial',
    }


def normalize_event_count(event_count, distance_km, driving_seconds):
    return {
        'events_per_100_km': round(event_count / distance_km * 100, 4) if distance_km > 0 else None,
        'events_per_driving_hour': round(event_count / (driving_seconds / 3600), 4) if driving_seconds > 0 else None,
    }
