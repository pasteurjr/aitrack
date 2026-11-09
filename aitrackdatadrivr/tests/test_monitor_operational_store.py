from pathlib import Path


def test_monitor_repository_does_not_write_legacy_operational_tables():
    source = (
        Path(__file__).resolve().parents[1] / 'server' / 'monitor_db.py'
    ).read_text(encoding='utf-8')

    for statement in (
        'INSERT INTO monitores',
        'UPDATE monitores',
        'INSERT INTO veiculomonitor',
        'UPDATE veiculomonitor',
        'INSERT INTO monitor_analises',
        'INSERT INTO monitor_alertas',
        'UPDATE monitor_alertas',
    ):
        assert statement not in source
    for table in (
        'monitoramento.monitores',
        'monitoramento.monitor_targets',
        'monitoramento.monitor_analises',
        'monitoramento.monitor_alertas',
    ):
        assert table in source
