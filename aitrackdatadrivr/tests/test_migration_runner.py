import importlib.util
from pathlib import Path
import stat

import pytest


RUNNER_PATH = Path(__file__).resolve().parents[1] / 'migrations' / 'apply.py'
SPEC = importlib.util.spec_from_file_location('migration_apply', RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_discovers_migrations_in_numeric_and_name_order(monkeypatch, tmp_path):
    for name in ('010_z.sql', '004_b.sql', '004_a.sql', 'readme.sql'):
        (tmp_path / name).write_text('-- teste', encoding='utf-8')
    monkeypatch.setattr(runner, 'MIGRATIONS_DIR', tmp_path)

    assert [(version, path.name) for version, path in runner.migration_files()] == [
        (4, '004_a.sql'), (4, '004_b.sql'), (10, '010_z.sql'),
    ]


def test_rejects_changed_applied_migration(tmp_path):
    path = tmp_path / '010_test.sql'
    path.write_text('SELECT 1;', encoding='utf-8')

    with pytest.raises(RuntimeError, match='foi alterada'):
        runner.validate_checksums([(10, path)], {path.name: '0' * 64})


def test_plan_excludes_applied_files(tmp_path):
    first = tmp_path / '009_old.sql'
    second = tmp_path / '010_new.sql'

    assert runner.plan([(9, first), (10, second)], {first.name: 'checksum'}) == [
        (10, second),
    ]


def test_mysql_credentials_file_is_private_and_removed(monkeypatch, tmp_path):
    sql = tmp_path / '010_test.sql'
    sql.write_text('SELECT 1;', encoding='utf-8')
    captured = {}

    def fake_run(command, stdin, check):
        defaults = Path(command[1].split('=', 1)[1])
        captured['path'] = defaults
        captured['mode'] = stat.S_IMODE(defaults.stat().st_mode)
        captured['content'] = defaults.read_text(encoding='utf-8')
        assert stdin.read() == b'SELECT 1;'
        assert check is True

    monkeypatch.setattr(runner.subprocess, 'run', fake_run)
    runner.execute_sql(sql, {
        'host': 'db', 'port': 3307, 'user': 'app', 'password': 'secret',
    })

    assert captured['mode'] == 0o600
    assert 'password=secret' in captured['content']
    assert not captured['path'].exists()


def test_database_config_refuses_non_tracker_metadata_database(monkeypatch, tmp_path):
    env = tmp_path / '.env'
    env.write_text(
        'AITRACK_DB_HOST=db\nAITRACK_DB_USER=app\n'
        'AITRACK_DB_PASSWORD=secret\nAITRACK_DB_NAME=outro\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(runner, 'ENV_FILE', env)
    for name in (
        'AITRACK_DB_HOST', 'AITRACK_DB_USER', 'AITRACK_DB_PASSWORD',
        'AITRACK_DB_NAME',
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match='deve ser tracker'):
        runner.database_config()
