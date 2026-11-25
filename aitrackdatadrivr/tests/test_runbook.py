from pathlib import Path

from scripts.validate_runbook import validate


def test_runbook_has_no_unsafe_commands_or_secrets_and_covers_required_topics():
    path = Path(__file__).parents[2] / 'docs' / 'RUNBOOK_OPERACAO_CONTINGENCIA.md'
    assert validate(path) == []
