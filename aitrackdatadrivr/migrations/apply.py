#!/usr/bin/env python3
"""Runner rastreável e seguro para migrations SQL do backend ativo."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

import mysql.connector


BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / 'config' / '.env'
BASELINE_MAX_VERSION = 9
BASELINE_REQUIREMENTS = {
    'tracker': {
        'tables': {
            'monitores', 'veiculomonitor', 'monitor_analises', 'monitor_alertas',
            'tipo_evento', 'eventos', 'veiculo_unificado', 'behavioral_scores',
            'incidents', 'incident_timeline',
        },
        'incident_columns': {
            'detection_outcome', 'classification_reason', 'classified_by',
            'classified_at',
        },
    },
}


def _load_env(path=None):
    path = path or ENV_FILE
    if not path.exists():
        raise RuntimeError(f'Arquivo de configuração ausente: {path}')
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_config():
    _load_env()
    required = ('AITRACK_DB_HOST', 'AITRACK_DB_USER', 'AITRACK_DB_PASSWORD')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f'Variáveis obrigatórias ausentes: {", ".join(missing)}')
    database = os.getenv('AITRACK_DB_NAME', 'tracker')
    if database != 'tracker':
        raise RuntimeError('AITRACK_DB_NAME deve ser tracker para executar migrations')
    return {
        'host': os.environ['AITRACK_DB_HOST'],
        'port': int(os.getenv('AITRACK_DB_PORT', '3306')),
        'user': os.environ['AITRACK_DB_USER'],
        'password': os.environ['AITRACK_DB_PASSWORD'],
        'database': database,
    }


def migration_files():
    files = []
    for path in MIGRATIONS_DIR.glob('[0-9][0-9][0-9]_*.sql'):
        try:
            version = int(path.name.split('_', 1)[0])
        except ValueError:
            continue
        files.append((version, path))
    return sorted(files, key=lambda item: (item[0], item[1].name))


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_metadata(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracker.schema_migrations (
              versao VARCHAR(255) NOT NULL,
              checksum CHAR(64) NOT NULL,
              aplicada_em DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
              PRIMARY KEY (versao)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        connection.commit()
    finally:
        cursor.close()


def applied_migrations(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = 'tracker' AND TABLE_NAME = 'schema_migrations'"
        )
        if not cursor.fetchone()['total']:
            return {}
        cursor.execute('SELECT versao, checksum FROM tracker.schema_migrations')
        return {row['versao']: row['checksum'] for row in cursor.fetchall()}
    finally:
        cursor.close()


def validate_baseline(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = 'tracker'"
        )
        tables = {row['TABLE_NAME'] for row in cursor.fetchall()}
        missing_tables = BASELINE_REQUIREMENTS['tracker']['tables'] - tables
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = 'tracker' AND TABLE_NAME = 'incidents'"
        )
        columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
        missing_columns = BASELINE_REQUIREMENTS['tracker']['incident_columns'] - columns
    finally:
        cursor.close()
    if missing_tables or missing_columns:
        details = []
        if missing_tables:
            details.append(f'tabelas: {sorted(missing_tables)}')
        if missing_columns:
            details.append(f'colunas: {sorted(missing_columns)}')
        raise RuntimeError('Baseline não pode ser confirmado; faltam ' + '; '.join(details))


def register(connection, path):
    cursor = connection.cursor()
    try:
        cursor.execute(
            'INSERT INTO tracker.schema_migrations (versao, checksum) VALUES (%s, %s)',
            (path.name, checksum(path)),
        )
        connection.commit()
    finally:
        cursor.close()


def baseline(connection, files):
    validate_baseline(connection)
    for version, path in files:
        if version <= BASELINE_MAX_VERSION:
            register(connection, path)


def validate_checksums(files, applied):
    paths = {path.name: path for _version, path in files}
    for name, recorded_checksum in applied.items():
        path = paths.get(name)
        if path and checksum(path) != recorded_checksum:
            raise RuntimeError(f'Migration aplicada foi alterada: {name}')


def _defaults_file(config):
    handle = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', prefix='aitrack-mysql-', suffix='.cnf',
        delete=False,
    )
    try:
        handle.write('[client]\n')
        handle.write(f"host={config['host']}\n")
        handle.write(f"port={config['port']}\n")
        handle.write(f"user={config['user']}\n")
        handle.write(f"password={config['password']}\n")
        handle.write('protocol=TCP\ndefault-character-set=utf8mb4\n')
        handle.close()
        os.chmod(handle.name, 0o600)
        return Path(handle.name)
    except Exception:
        handle.close()
        Path(handle.name).unlink(missing_ok=True)
        raise


def execute_sql(path, config):
    defaults = _defaults_file(config)
    try:
        with path.open('rb') as sql_file:
            subprocess.run(
                ['mysql', f'--defaults-extra-file={defaults}', '--binary-mode=1'],
                stdin=sql_file,
                check=True,
            )
    finally:
        defaults.unlink(missing_ok=True)


def plan(files, applied):
    return [(version, path) for version, path in files if path.name not in applied]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='lista sem escrever')
    parser.add_argument(
        '--baseline-only', action='store_true',
        help='registra migrations 001–009 já confirmadas e não aplica pendências',
    )
    args = parser.parse_args(argv)
    config = database_config()
    connection = mysql.connector.connect(**config)
    try:
        files = migration_files()
        applied = applied_migrations(connection)
        if applied:
            validate_checksums(files, applied)
        pending = plan(files, applied)
        if args.dry_run:
            if not applied:
                print('baseline pendente: migrations 001–009 serão somente registradas')
            for _version, path in pending:
                action = 'baseline' if int(path.name[:3]) <= BASELINE_MAX_VERSION else 'aplicar'
                print(f'{action}: {path.name}')
            if not pending:
                print('0 migrations pendentes')
            return 0

        ensure_metadata(connection)
        if not applied:
            baseline(connection, files)
            applied = applied_migrations(connection)
        if args.baseline_only:
            print('baseline confirmado; nenhuma migration nova foi aplicada')
            return 0

        for _version, path in plan(files, applied):
            print(f'aplicando {path.name}')
            execute_sql(path, config)
            register(connection, path)
        print('migrations concluídas')
        return 0
    finally:
        connection.close()


if __name__ == '__main__':
    raise SystemExit(main())
