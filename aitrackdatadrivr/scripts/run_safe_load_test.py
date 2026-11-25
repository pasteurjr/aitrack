#!/usr/bin/env python3
"""Carga/recovery determinísticos em SQLite temporário; nunca usa banco compartilhado."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from time import perf_counter
from urllib.parse import urlparse


def assert_local_target(value):
    if not value:
        return
    parsed = urlparse(value)
    if parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Carga recusada: somente alvo loopback isolado é permitido')


def percentile(values, percentage):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentage)))
    return ordered[index]


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE receipts(correlation_id TEXT PRIMARY KEY, received_at TEXT NOT NULL);
CREATE TABLE incidents(correlation_id TEXT PRIMARY KEY, state TEXT NOT NULL);
CREATE TABLE actions(correlation_id TEXT PRIMARY KEY, state TEXT NOT NULL);
CREATE TABLE jobs(id INTEGER PRIMARY KEY, correlation_id TEXT UNIQUE NOT NULL,
                  state TEXT NOT NULL, lease_until INTEGER NULL);
"""


def connect(path):
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    connection.execute('PRAGMA busy_timeout=30000')
    return connection


def ingest_batch(path, keys):
    connection = connect(path); latencies = []
    try:
        for key in keys:
            started = perf_counter()
            connection.execute('BEGIN IMMEDIATE')
            try:
                inserted = connection.execute(
                    'INSERT OR IGNORE INTO receipts VALUES(?,?)',
                    (key, datetime.now(timezone.utc).isoformat()),
                ).rowcount
                if inserted:
                    connection.execute('INSERT INTO incidents VALUES(?,?)', (key, 'open'))
                    connection.execute('INSERT INTO actions VALUES(?,?)', (key, 'pending'))
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK'); raise
            latencies.append((perf_counter() - started) * 1000)
        return latencies
    finally:
        connection.close()


def run(iterations=2000, workers=4):
    if iterations < 100 or workers < 1 or workers > 32:
        raise ValueError('iterations >= 100 e workers entre 1 e 32')
    with tempfile.TemporaryDirectory(prefix='aitrack-load-') as temp_dir:
        path = Path(temp_dir) / 'isolated.sqlite3'
        connection = connect(path); connection.executescript(SCHEMA); connection.close()
        keys = [f'packet-{index:08d}' for index in range(iterations)]
        chunks = [keys[index::workers] for index in range(workers)]
        started = perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            latency_groups = list(executor.map(lambda chunk: ingest_batch(path, chunk), chunks))
        sustained_seconds = perf_counter() - started
        latencies = [value for group in latency_groups for value in group]

        # Replay completo deve ser absorvido pelas mesmas chaves.
        replay_latencies = ingest_batch(path, keys)
        connection = connect(path)
        before_restart = {
            table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            for table in ('receipts', 'incidents', 'actions')
        }
        connection.executemany(
            "INSERT INTO jobs(correlation_id,state,lease_until) VALUES(?,'claimed',0)",
            [(f'job-{index}',) for index in range(100)],
        )
        connection.close()  # restart real da conexão/processo de persistência

        recovery_started = perf_counter(); connection = connect(path)
        connection.execute("UPDATE jobs SET state='pending',lease_until=NULL WHERE state='claimed' AND lease_until<1")
        connection.execute("UPDATE jobs SET state='completed' WHERE state='pending'")
        recovered_jobs = connection.execute("SELECT COUNT(*) FROM jobs WHERE state='completed'").fetchone()[0]
        after_restart = {
            table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            for table in ('receipts', 'incidents', 'actions')
        }
        duplicate_counts = {
            table: connection.execute(
                f'SELECT COUNT(*) FROM (SELECT correlation_id FROM {table} GROUP BY correlation_id HAVING COUNT(*)>1)'
            ).fetchone()[0]
            for table in ('receipts', 'incidents', 'actions')
        }
        connection.close(); rto_seconds = perf_counter() - recovery_started

    result = {
        'schema_version': 'safe-load-result.v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'environment': 'isolated-temporary-sqlite',
        'iterations': iterations, 'workers': workers,
        'throughput_per_second': round(iterations / sustained_seconds, 2),
        'p95_persist_ms': round(percentile(latencies, .95), 3),
        'p99_persist_ms': round(percentile(latencies, .99), 3),
        'p95_replay_ms': round(percentile(replay_latencies, .95), 3),
        'before_restart': before_restart, 'after_restart': after_restart,
        'duplicate_counts': duplicate_counts, 'recovered_expired_leases': recovered_jobs,
        'rpo_records_lost': sum(before_restart.values()) - sum(after_restart.values()),
        'rto_seconds': round(rto_seconds, 4),
    }
    result['passed'] = (
        result['p95_persist_ms'] <= 20 and result['p99_persist_ms'] <= 100
        and not any(duplicate_counts.values()) and result['rpo_records_lost'] == 0
        and recovered_jobs == 100 and rto_seconds <= 5
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--base-url', help='Opcional; deve ser loopback (não recebe tráfego neste harness)')
    args = parser.parse_args(argv)
    assert_local_target(args.base_url)
    print(json.dumps(run(args.iterations, args.workers), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
