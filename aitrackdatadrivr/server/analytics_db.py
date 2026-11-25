"""Agregações históricas limitadas por período e origem."""

from .monitor_db import get_connection
from .analytics_exposure import FORMULA_VERSION, normalize_event_count


SOURCES = {'tracker', 'dirijabem'}
SOURCE_SQL = "COALESCE(JSON_UNQUOTE(JSON_EXTRACT(e.dados_adicionais, '$.source')), 'tracker')"


def parse_sources(raw):
    values = [item.strip().lower() for item in str(raw or 'tracker,dirijabem').split(',') if item.strip()]
    if not values or set(values) - SOURCES:
        raise ValueError('sources aceita somente tracker e dirijabem')
    return tuple(dict.fromkeys(values))


def aggregate_behavior(period, sources, connection=None):
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor(dictionary=True)
    source_placeholders = ','.join(['%s'] * len(sources))
    params = (period.start_utc, period.end_utc, *sources)
    try:
        cursor.execute(
            f"""SELECT {SOURCE_SQL} source, te.codigo event_type, COUNT(*) total
                  FROM tracker.eventos e
                  JOIN tracker.tipo_evento te ON te.id=e.tipo_evento_id
                 WHERE e.timestamp >= %s AND e.timestamp < %s
                   AND {SOURCE_SQL} IN ({source_placeholders})
                 GROUP BY source, te.codigo
                 ORDER BY source, total DESC, te.codigo""",
            params,
        )
        by_type = cursor.fetchall()
        cursor.execute(
            f"""SELECT {SOURCE_SQL} source, e.device_id, COUNT(*) total
                  FROM tracker.eventos e
                 WHERE e.timestamp >= %s AND e.timestamp < %s
                   AND {SOURCE_SQL} IN ({source_placeholders})
                 GROUP BY source, e.device_id
                 ORDER BY total DESC, source, e.device_id LIMIT 100""",
            params,
        )
        by_vehicle = cursor.fetchall()
        cursor.execute(
            f"""SELECT source, SUM(distance_km) distance_km,
                       SUM(driving_seconds) driving_seconds,
                       SUM(valid_points) valid_points,
                       SUM(discarded_points) discarded_points,
                       COUNT(*) bucket_count
                  FROM monitoramento.analytics_exposure_buckets
                 WHERE bucket_start >= %s AND bucket_end <= %s
                   AND formula_version=%s
                   AND source IN ({source_placeholders})
                 GROUP BY source""",
            (period.start_utc, period.end_utc, FORMULA_VERSION, *sources),
        )
        exposure_rows = {row['source']: row for row in cursor.fetchall()}
    finally:
        cursor.close()
        if owns_connection:
            conn.close()

    source_totals = {source: 0 for source in sources}
    for row in by_type:
        source_totals[row['source']] = source_totals.get(row['source'], 0) + row['total']
    exposure = {}
    for source in sources:
        row = exposure_rows.get(source)
        valid = int(row['valid_points']) if row else 0
        discarded = int(row['discarded_points']) if row else 0
        total_points = valid + discarded
        exposure[source] = {
            'distance_km': float(row['distance_km']) if row else 0.0,
            'driving_seconds': int(row['driving_seconds']) if row else 0,
            'valid_points': valid,
            'discarded_points': discarded,
            'coverage': valid / total_points if total_points else 0.0,
            'quality': 'unavailable' if not row else 'complete' if not discarded else 'partial',
            'bucket_count': int(row['bucket_count']) if row else 0,
            'formula_version': FORMULA_VERSION,
        }
    normalized_by_type = []
    for row in by_type:
        source_exposure = exposure[row['source']]
        normalized_by_type.append({
            **row,
            **normalize_event_count(
                row['total'], source_exposure['distance_km'], source_exposure['driving_seconds']
            ),
        })
    return {
        'period': period.public(),
        'sources': list(sources),
        'total_events': sum(source_totals.values()),
        'source_totals': source_totals,
        'by_type': by_type,
        'normalized_by_type': normalized_by_type,
        'by_vehicle': by_vehicle,
        'exposure': exposure,
        'exposure_formula_version': FORMULA_VERSION,
    }
