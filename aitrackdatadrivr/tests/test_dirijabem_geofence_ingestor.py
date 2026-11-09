from datetime import datetime

from server import dirijabem_geofence_ingestor as ingestor
from server.dirijabem_geofence_ingestor import rewind_start


def test_rewind_keeps_overlap_for_out_of_order_commits():
    assert rewind_start(20_000, window=10_000) == 10_000
    assert rewind_start(500, window=10_000) == 0


class FakeCursor:
    def __init__(self, attempts=1):
        self.attempts = attempts
        self.one = None
        self.many = []
        self.statements = []

    def execute(self, sql, params=()):
        normalized = ' '.join(sql.split())
        self.statements.append((normalized, params))
        if 'SELECT last_external_id' in normalized:
            self.one = {'last_external_id': 100}
        elif 'SELECT l.LOCDADCOD AS position_id' in normalized:
            self.many = [
                {
                    'position_id': 101, 'observed_at': datetime(2026, 1, 1),
                    'longitude': -46.6, 'latitude': -23.5,
                    'user_id': 1, 'plate': 'TESTE',
                },
                {
                    'position_id': 102, 'observed_at': datetime(2026, 1, 1),
                    'longitude': -46.6, 'latitude': -23.5,
                    'user_id': 1, 'plate': 'TESTE',
                },
            ]
        elif 'SELECT attempts FROM monitoramento.source_ingestion_failures' in normalized:
            self.one = {'attempts': self.attempts}

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many

    def close(self):
        pass


class FakeConnection:
    def __init__(self, attempts=1):
        self.cursor_instance = FakeCursor(attempts)
        self.commits = 0

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


def test_poll_continues_after_bad_row_and_advances_watermark(monkeypatch):
    connection = FakeConnection(attempts=1)
    evaluated = []

    def evaluate(**kwargs):
        evaluated.append(kwargs['external_position_id'])
        if kwargs['external_position_id'] == 101:
            raise ValueError('posição inválida')

    monkeypatch.setattr(ingestor, 'get_connection', lambda: connection)
    monkeypatch.setattr(ingestor, 'evaluate_dirijabem_position', evaluate)

    assert ingestor.poll_once() == 2
    assert evaluated == [101, 102]
    statements = [sql for sql, _params in connection.cursor_instance.statements]
    assert any('source_ingestion_failures' in sql for sql in statements)
    assert any('SET last_external_id = %s' in sql for sql in statements)


def test_poll_quarantines_after_retry_limit(monkeypatch):
    connection = FakeConnection(attempts=ingestor.MAX_FAILURE_ATTEMPTS)
    monkeypatch.setattr(ingestor, 'get_connection', lambda: connection)
    monkeypatch.setattr(
        ingestor,
        'evaluate_dirijabem_position',
        lambda **_kwargs: (_ for _ in ()).throw(ValueError('permanente')),
    )

    assert ingestor.poll_once() == 2
    statements = [sql for sql, _params in connection.cursor_instance.statements]
    assert any("SET status = 'quarantined'" in sql for sql in statements)
    assert any('source_position_receipts' in sql for sql in statements)
