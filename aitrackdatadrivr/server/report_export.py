"""Serialização segura de relatórios e cálculo de agenda local."""

import csv
from datetime import datetime, timedelta, timezone
import io
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


FORMATS = {'csv', 'json'}


def safe_csv_cell(value):
    text = '' if value is None else str(value)
    return "'" + text if text.startswith(('=', '+', '-', '@')) else text


def report_rows(report):
    summary = report['summary']
    rows = []
    for source, values in summary['source_breakdown'].items():
        rows.append({
            'report_public_id': report['public_id'],
            'mode': summary['mode'],
            'source': source,
            'event_count': values['event_count'],
            'distance_km': values['distance_km'],
            'driving_seconds': values['driving_seconds'],
            'quality': values['quality'],
            'formula_version': report['formula_version'],
            'period_from': report['filters']['from'],
            'period_to': report['filters']['to'],
        })
    return rows


def serialize_report(report, export_format):
    if export_format not in FORMATS:
        raise ValueError('format deve ser csv ou json')
    rows = report_rows(report)
    if export_format == 'json':
        content = json.dumps({
            'schema_version': 'behavior-report-export.v1',
            'report_public_id': report['public_id'],
            'filters': report['filters'],
            'formula_version': report['formula_version'],
            'rows': rows,
        }, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    else:
        output = io.StringIO(newline='')
        fields = list(rows[0]) if rows else ['report_public_id']
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_csv_cell(value) for key, value in row.items()})
        content = output.getvalue()
    return content.encode('utf-8'), len(rows)


def next_schedule_run(cadence, local_time, timezone_name, weekday=None, after=None):
    if cadence not in {'daily', 'weekly'}:
        raise ValueError('cadence deve ser daily ou weekly')
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('timezone inválido') from exc
    hour, minute = [int(part) for part in local_time.split(':')[:2]]
    reference = (after or datetime.now(timezone.utc)).astimezone(zone)
    candidate = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if cadence == 'daily':
        if candidate <= reference:
            candidate += timedelta(days=1)
    else:
        if weekday is None or not 0 <= int(weekday) <= 6:
            raise ValueError('weekday entre 0 e 6 é obrigatório para weekly')
        candidate += timedelta(days=(int(weekday) - candidate.weekday()) % 7)
        if candidate <= reference:
            candidate += timedelta(days=7)
    return candidate.astimezone(timezone.utc).replace(tzinfo=None)
