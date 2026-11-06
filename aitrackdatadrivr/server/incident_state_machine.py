"""Regras determinísticas de ciclo de vida dos incidentes."""

from datetime import datetime
from typing import Dict, Optional


class InvalidTransition(ValueError):
    pass


TRANSITIONS = {
    ('new', 'triage'): 'triage',
    ('triage', 'start_service'): 'in_progress',
    ('triage', 'resolve'): 'resolved',
    ('in_progress', 'wait_response'): 'waiting_response',
    ('in_progress', 'escalate'): 'escalated',
    ('in_progress', 'resolve'): 'resolved',
    ('waiting_response', 'resume'): 'in_progress',
    ('waiting_response', 'escalate'): 'escalated',
    ('waiting_response', 'resolve'): 'resolved',
    ('escalated', 'resume'): 'in_progress',
    ('escalated', 'wait_response'): 'waiting_response',
    ('escalated', 'resolve'): 'resolved',
    ('resolved', 'close'): 'closed',
    ('resolved', 'reopen'): 'triage',
    ('closed', 'reopen'): 'triage',
}

COMMAND_LABELS = {
    'triage': 'Incidente encaminhado para triagem',
    'start_service': 'Atendimento iniciado',
    'wait_response': 'Incidente aguardando resposta',
    'escalate': 'Incidente escalado',
    'resume': 'Atendimento retomado',
    'resolve': 'Incidente resolvido',
    'close': 'Incidente encerrado',
    'reopen': 'Incidente reaberto para triagem',
}


def plan_transition(
    incident: Dict,
    command: str,
    payload: Optional[Dict] = None,
    now: Optional[datetime] = None,
) -> Dict:
    if not isinstance(incident, dict) or not incident.get('status'):
        raise InvalidTransition('Incidente sem estado válido')
    if not isinstance(command, str) or not command.strip():
        raise InvalidTransition('Comando de transição é obrigatório')
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise InvalidTransition('Dados da transição devem ser um objeto')

    command = command.strip()
    now = now or datetime.now()
    current_status = incident['status']
    target_status = TRANSITIONS.get((current_status, command))
    if target_status is None:
        raise InvalidTransition(
            f'Comando {command!r} não permitido para incidente em {current_status!r}'
        )

    updates = {'status': target_status}
    if command == 'triage':
        updates['triaged_at'] = now
    elif command == 'start_service':
        assigned_type = payload.get('assigned_type')
        assigned_to = str(payload.get('assigned_to') or '').strip()
        if assigned_type not in {'human', 'agent'} or not assigned_to:
            raise InvalidTransition('Iniciar atendimento exige responsável humano ou agente')
        if len(assigned_to) > 100:
            raise InvalidTransition('Responsável deve ter no máximo 100 caracteres')
        updates.update({
            'assigned_type': assigned_type,
            'assigned_to': assigned_to,
            'acknowledged_at': incident.get('acknowledged_at') or now,
        })
    elif command == 'wait_response':
        if payload.get('next_action_at') is None:
            raise InvalidTransition('Aguardar resposta exige next_action_at')
        updates['next_action_at'] = payload['next_action_at']
    elif command == 'resolve':
        resolution_code = str(payload.get('resolution_code') or '').strip()
        resolution_notes = str(payload.get('resolution_notes') or '').strip()
        if not resolution_code or len(resolution_notes) < 5:
            raise InvalidTransition('Resolver exige código e justificativa com pelo menos 5 caracteres')
        if len(resolution_code) > 50:
            raise InvalidTransition('Código de resolução deve ter no máximo 50 caracteres')
        false_positive = bool(payload.get('false_positive', False))
        if false_positive and resolution_code != 'false_positive':
            raise InvalidTransition('Falso positivo exige resolution_code=false_positive')
        updates.update({
            'resolution_code': resolution_code,
            'resolution_notes': resolution_notes,
            'false_positive': false_positive,
            'resolved_at': now,
            'next_action_at': None,
        })
    elif command == 'close':
        if not incident.get('resolution_code'):
            raise InvalidTransition('Encerrar exige resolução registrada')
        updates['closed_at'] = now
        updates['next_action_at'] = None
    elif command == 'reopen':
        updates.update({
            'triaged_at': now,
            'resolved_at': None,
            'closed_at': None,
            'resolution_code': None,
            'resolution_notes': None,
            'false_positive': False,
        })

    summary = str(payload.get('summary') or COMMAND_LABELS[command]).strip()
    if not summary or len(summary) > 300:
        raise InvalidTransition('Resumo deve ter entre 1 e 300 caracteres')
    return {
        'command': command,
        'from_status': current_status,
        'to_status': target_status,
        'updates': updates,
        'summary': summary,
    }
