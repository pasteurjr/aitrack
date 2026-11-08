import importlib.util
from pathlib import Path


BACKFILL_PATH = (
    Path(__file__).resolve().parents[1]
    / 'migrations'
    / 'backfill_operational_monitors.py'
)
SPEC = importlib.util.spec_from_file_location('monitor_backfill', BACKFILL_PATH)
backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backfill)


def test_analysis_copy_preserves_scoring_conclusion_and_severity():
    for column in (
        'periodo_inicio', 'periodo_fim', 'total_eventos', 'score_inicial',
        'score_final', 'eventos_por_tipo', 'conclusao', 'severidade',
    ):
        assert column in backfill.ANALYSIS_COLUMNS


def test_alert_copy_preserves_lifecycle_and_operator_audit():
    for column in (
        'status', 'reconhecido_em', 'reconhecido_por', 'criado_em',
        'total_eventos_relacionados',
    ):
        assert column in backfill.ALERT_COLUMNS
