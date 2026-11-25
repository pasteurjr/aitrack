"""Contrato determinístico e somente leitura para replay de viagens."""

from datetime import datetime


EVENT_ORDER = {
    'execution': 0,
    'position': 1,
    'episode_started': 2,
    'episode_recovered': 3,
}
ALLOWED_SPEEDS = (0.5, 1.0, 2.0, 4.0)


def merge_timeline(*event_groups):
    """Mescla eventos sem alterar timestamps, com desempate estável."""
    events = [dict(event) for group in event_groups for event in group]
    for event in events:
        if not isinstance(event.get('occurred_at'), datetime):
            raise ValueError('occurred_at deve ser datetime')
        if event.get('kind') not in EVENT_ORDER:
            raise ValueError('kind de replay inválido')
    return sorted(
        events,
        key=lambda event: (
            event['occurred_at'],
            EVENT_ORDER[event['kind']],
            str(event.get('stable_id', '')),
        ),
    )


def validate_speed(value):
    speed = float(value)
    if speed not in ALLOWED_SPEEDS:
        raise ValueError('Velocidade deve ser 0.5, 1, 2 ou 4')
    return speed


def serialize_event(event):
    result = dict(event)
    result['occurred_at'] = result['occurred_at'].isoformat()
    return result
