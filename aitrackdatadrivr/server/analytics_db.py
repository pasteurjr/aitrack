"""Agregações históricas limitadas por período e origem."""

from .monitor_db import get_connection


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
    finally:
        cursor.close()
        if owns_connection:
            conn.close()

    source_totals = {source: 0 for source in sources}
    for row in by_type:
        source_totals[row['source']] = source_totals.get(row['source'], 0) + row['total']
    return {
        'period': period.public(),
        'sources': list(sources),
        'total_events': sum(source_totals.values()),
        'source_totals': source_totals,
        'by_type': by_type,
        'by_vehicle': by_vehicle,
    }
