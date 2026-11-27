#!/usr/bin/env python3
"""Exercise selected application recovery paths in disposable MariaDB instances."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from time import monotonic, sleep

import mysql.connector


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
MIGRATIONS = (10, 12, 14, 15, 17, 18, 23, 24, 25, 28, 29, 32, 33, 42, 43, 66)
SNAPSHOT_QUERIES = {
    'source_receipts': 'SELECT * FROM monitoramento.source_position_receipts ORDER BY source_code, external_position_id',
    'incidents': 'SELECT * FROM monitoramento.incidents ORDER BY id',
    'actions': 'SELECT * FROM monitoramento.action_queue ORDER BY id',
    'action_events': 'SELECT * FROM monitoramento.action_events ORDER BY id',
    'triggers': "SELECT TRIGGER_NAME, ACTION_STATEMENT FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='monitoramento' ORDER BY TRIGGER_NAME",
}

API_PROCESS = """
import json, sys
import mysql.connector
from werkzeug.serving import make_server

open_connection = mysql.connector.connect
def private_connection(**config):
    if config.get('database') != 'monitoramento':
        raise RuntimeError('Only the isolated operational schema is allowed')
    return open_connection(unix_socket=sys.argv[1], user=sys.argv[2],
                           database='monitoramento', use_pure=True, connection_timeout=2)

mysql.connector.connect = private_connection
from server.api import app

with make_server('127.0.0.1', 0, app) as server:
    print(json.dumps({'port': server.server_port}), flush=True)
    server.serve_forever()
"""


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


@contextmanager
def process(args, **options):
    with subprocess.Popen(args, **options) as child:
        try:
            yield child
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


class Database:
    def __init__(self, directory):
        self.directory = directory
        self.socket = directory / 'db.sock'
        self.user = getpass.getuser()
        directory.mkdir(mode=0o700)
        subprocess.run([
            'mariadb-install-db', '--no-defaults', f'--datadir={directory}',
            '--auth-root-authentication-method=socket', f'--auth-root-socket-user={self.user}',
            '--skip-test-db',
        ], check=True, capture_output=True, timeout=60)

    def client(self, command='mariadb'):
        return [command, '--no-defaults', '--protocol=socket', f'--socket={self.socket}', f'--user={self.user}']

    @contextmanager
    def start(self):
        with process([
            'mariadbd', '--no-defaults', '--skip-networking', f'--datadir={self.directory}',
            f'--socket={self.socket}', f'--pid-file={self.directory / "db.pid"}',
            f'--log-error={self.directory / "db.log"}',
        ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as daemon:
            deadline = monotonic() + 20
            while daemon.poll() is None and monotonic() < deadline:
                if self.socket.exists() and subprocess.run(
                    [*self.client(), '-e', 'SELECT 1'], capture_output=True, timeout=3,
                ).returncode == 0:
                    yield
                    return
                sleep(0.1)
            raise RuntimeError(f'MariaDB failed to start: {(self.directory / "db.log").read_text()[-2000:]}')

    def sql(self, content):
        result = subprocess.run(self.client(), input=content, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])

    def connect(self):
        return mysql.connector.connect(unix_socket=str(self.socket), user=self.user,
                                       database='monitoramento', use_pure=True, connection_timeout=2)

    def dump(self):
        return subprocess.check_output([
            *self.client('mariadb-dump'), '--single-transaction', '--skip-add-drop-table',
            '--triggers', '--databases', 'monitoramento',
        ], timeout=30)


def release(ref, directory):
    git = ['git', '-C', str(REPOSITORY)]
    sha = subprocess.check_output([*git, 'rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}'], text=True).strip()
    directory.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output([
        *git, 'archive', sha, 'aitrackdatadrivr',
    ])), mode='r:') as archive:
        archive.extractall(directory, filter='data')
    return sha, directory / 'aitrackdatadrivr'


@contextmanager
def api(release_directory, database):
    code = f'import sys; sys.path.insert(0, {str(release_directory)!r});\n' + API_PROCESS
    with process(
        [sys.executable, '-c', code, str(database.socket), database.user],
        cwd=database.directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
        env={**{k: os.environ[k] for k in ('PATH',) if k in os.environ},
             'AITRACK_OPERATION_MODE': 'simulation', 'AITRACK_DB_HOST': 'isolated.invalid',
             'AITRACK_DB_USER': database.user, 'AITRACK_DB_PASSWORD': 'socket-only-placeholder',
             'AITRACK_DB_NAME': 'monitoramento'},
    ) as child:
        import select
        require(select.select([child.stdout], [], [], 15)[0], 'API startup timed out')
        line = child.stdout.readline()
        require(line, 'API exited before startup')
        yield json.loads(line)['port']


def health(port, path, expected):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        conn.request('GET', f'/api/health/{path}')
        response = conn.getresponse()
        data = json.loads(response.read())
        require(response.status == expected, f'{path}: expected HTTP {expected}, got {response.status}')
        return data
    finally:
        conn.close()


def snapshot(database):
    with database.connect() as conn, conn.cursor() as cursor:
        records = {}
        for name, query in SNAPSHOT_QUERIES.items():
            cursor.execute(query)
            records[name] = cursor.fetchall()
        return records


def seed(database, current):
    sys.path.insert(0, str(current))
    from server.action_queue_db import create_action, transition_action

    for number in MIGRATIONS:
        migration, = (PROJECT / 'migrations').glob(f'{number:03}_*.sql')
        database.sql(migration.read_bytes())
    database.sql(b"""
        UPDATE monitoramento.health_components SET status='healthy' WHERE component_key='action_worker';
        UPDATE monitoramento.integration_health SET status='healthy' WHERE source_code IN ('tracker','dirijabem');
        INSERT INTO monitoramento.veiculos (id, public_id, descricao) VALUES (1, UUID(), 'R7 sintetico');
        INSERT INTO monitoramento.incidents (id, correlation_key, vehicle_id, incident_type, title, severity, primary_source)
          VALUES (1, 'r7-tracker', 1, 'geofence_exit', 'R7 Tracker', 'high', 'tracker'),
                 (2, 'r7-dirijabem', 1, 'harsh_brake', 'R7 Dirija Bem', 'medium', 'dirijabem');
        INSERT INTO monitoramento.source_position_receipts (source_code, external_position_id, received_at)
          VALUES ('tracker', 'r7-pos-1', NOW(6)), ('dirijabem', 'r7-pos-2', NOW(6));
    """)
    actions = []
    with database.connect() as conn:
        for suffix, incident, state, attempts in (
            ('retry', 1, 'pending', 2), ('dead', 2, 'pending', 1), ('final', 2, 'simulated', 1),
        ):
            payload = {'action_type': 'internal_notification', 'target_type': 'operator',
                       'target_ref': 'r7-test', 'payload': {}, 'policy_snapshot': {},
                       'status': state, 'incident_id': incident, 'max_attempts': attempts,
                       'idempotency_key': f'r7-{suffix}', 'correlation_id': f'r7-{suffix}'}
            action = create_action(payload, connection=conn)
            actions.append(payload)
            if state == 'pending':
                transition_action(action['public_id'], 'claim', {
                    'expected_version': action['version'], 'idempotency_key': f'r7-{suffix}:claim',
                    'actor_type': 'system', 'worker_id': 'r7-test', 'lease_seconds': 10,
                }, connection=conn)
        conn.commit()
    return actions


def exercise(root, current_ref, previous_ref):
    current_sha, current = release(current_ref, root / 'current')
    previous_sha, previous = release(previous_ref, root / 'previous')
    require(current_sha != previous_sha, 'Rollback requires distinct revisions')
    primary, restored = (Database(root / name) for name in ('primary', 'restored'))
    with primary.start():
        actions = seed(primary, current)
        original = snapshot(primary)
        with api(current, primary) as port:
            health(port, 'live', 200)
            health(port, 'ready', 200)
        backup = primary.dump()

    started = monotonic()
    with primary.start():
        with api(current, primary) as port:
            health(port, 'ready', 200)
            restart_seconds = monotonic() - started
        require(snapshot(primary) == original, 'Records changed after MariaDB and API restart')

    started = monotonic()
    with restored.start():
        restored.sql(backup)
        require(snapshot(restored) == original, 'Restored rows or triggers differ from snapshot')
        with api(current, restored) as port:
            health(port, 'ready', 200)
            restore_seconds = monotonic() - started
        started = monotonic()
        with api(previous, restored) as port:
            health(port, 'live', 200)
            health(port, 'ready', 200)
            rollback_seconds = monotonic() - started
        require(snapshot(restored) == original, 'Records changed after application rollback')
        with api(current, restored) as port:
            health(port, 'ready', 200)

        from server import action_retry_db
        from server.action_queue_db import create_action

        action_retry_db.get_connection = restored.connect
        now = datetime.now() + timedelta(minutes=1)
        recovered = action_retry_db.recover_expired_claims(now=now)
        require(recovered == {'retried': 1, 'dead': 1, 'processed': 2}, 'Unexpected lease dispositions')
        require(action_retry_db.recover_expired_claims(now=now)['processed'] == 0, 'Lease recovery duplicated work')
        with restored.connect() as conn:
            for expected, payload in zip(('pending', 'dead', 'simulated'), actions, strict=True):
                replay = create_action(payload, connection=conn)
                require(replay['idempotent_replay'] and replay['status'] == expected, 'Replay changed action state')
            conn.commit()
        final = snapshot(restored)
        for kind in ('source_receipts', 'incidents', 'triggers'):
            require(final[kind] == original[kind], f'Recovery changed {kind}')
        require(len(final['actions']) == 3 and len(final['action_events']) == 9, 'Unexpected counts after replay')
        require(set(original['action_events']).issubset(final['action_events']), 'Recovery removed previous events')

    return {
        'schema_version': 'local-recovery-drill.v1', 'passed': True,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'current_release': current_sha, 'rollback_release': previous_sha,
        'environment': 'private MariaDB sockets and loopback HTTP', 'migration_numbers': MIGRATIONS,
        'backup_bytes': len(backup), 'backup_sha256': hashlib.sha256(backup).hexdigest(),
        'restart_to_ready_seconds': round(restart_seconds, 3),
        'restore_to_ready_seconds': round(restore_seconds, 3),
        'rollback_to_ready_seconds': round(rollback_seconds, 3),
        'backup_and_restart_counts': {name: len(items) for name, items in original.items()},
        'restored_rows_and_triggers_match': True,
        'lost_records_at_backup_cut': 0, 'duplicate_actions_on_replay': 0,
        'recovered_leases': recovered, 'second_recovery_processed': 0,
        'final_action_events': len(final['action_events']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', default='HEAD')
    parser.add_argument('--previous', required=True)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='aitrack-r7-', dir='/tmp') as directory:
        result = exercise(Path(directory), args.current, args.previous)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
