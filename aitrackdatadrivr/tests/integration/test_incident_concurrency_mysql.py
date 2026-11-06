"""Provas de concorrência contra o MariaDB real.

Estes testes são opt-in porque escrevem registros temporários no banco
compartilhado. Todos os registros são removidos por ID no bloco ``finally``.
"""

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from server.incident_db import (
    IncidentConflict,
    add_incident_comment,
    get_connection,
    transition_incident,
)


pytestmark = pytest.mark.skipif(
    os.getenv('AITRACK_RUN_DB_INTEGRATION') != '1',
    reason='exige AITRACK_RUN_DB_INTEGRATION=1 e acesso ao MariaDB compartilhado',
)

ACTOR_A = {'type': 'human', 'id': 'ui210-a', 'name': 'Operador Concorrente A'}
ACTOR_B = {'type': 'human', 'id': 'ui210-b', 'name': 'Operador Concorrente B'}


def _create_incident(status='new'):
    """Cria um incidente isolado e devolve seu ID já confirmado."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT id FROM tracker.veiculo_unificado WHERE ativo = TRUE ORDER BY id LIMIT 1'
        )
        vehicle = cursor.fetchone()
        if not vehicle:
            pytest.skip('nenhum veículo unificado ativo disponível')
        key = f'ui210:{uuid.uuid4()}'
        cursor.execute(
            """
            INSERT INTO tracker.incidents
                (correlation_key, vehicle_id, incident_type, title, summary,
                 status, severity, primary_source, version)
            VALUES (%s, %s, 'concurrency_test', 'Teste concorrente UI-2.10',
                    'Registro temporário removido automaticamente', %s,
                    'low', 'system', 1)
            """,
            (key, vehicle['id'], status),
        )
        incident_id = cursor.lastrowid
        conn.commit()
        return incident_id
    finally:
        cursor.close()
        conn.close()


def _delete_incident(incident_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'DELETE FROM tracker.incident_timeline WHERE incident_id = %s',
            (incident_id,),
        )
        cursor.execute('DELETE FROM tracker.incidents WHERE id = %s', (incident_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _run_simultaneously(*operations):
    barrier = threading.Barrier(len(operations))

    def execute(operation):
        barrier.wait(timeout=10)
        try:
            return operation()
        except Exception as exc:  # o resultado concorrente inclui conflitos esperados
            return exc

    with ThreadPoolExecutor(max_workers=len(operations)) as executor:
        futures = [executor.submit(execute, operation) for operation in operations]
        return [future.result(timeout=20) for future in futures]


def _database_state(incident_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT status, version FROM tracker.incidents WHERE id = %s',
            (incident_id,),
        )
        incident = cursor.fetchone()
        cursor.execute(
            'SELECT entry_type, idempotency_key FROM tracker.incident_timeline '
            'WHERE incident_id = %s ORDER BY id',
            (incident_id,),
        )
        return incident, cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def test_simultaneous_retry_executes_transition_once_and_replays_once():
    incident_id = _create_incident('new')
    idempotency_key = f'ui210-retry:{uuid.uuid4()}'
    try:
        results = _run_simultaneously(
            lambda: transition_incident(
                incident_id, 'triage', {}, ACTOR_A, 1, idempotency_key,
            ),
            lambda: transition_incident(
                incident_id, 'triage', {}, ACTOR_A, 1, idempotency_key,
            ),
        )

        assert all(isinstance(result, dict) for result in results)
        assert sorted(result['idempotent_replay'] for result in results) == [False, True]
        incident, timeline = _database_state(incident_id)
        assert incident == {'status': 'triage', 'version': 2}
        assert timeline == [{
            'entry_type': 'status_changed',
            'idempotency_key': idempotency_key,
        }]
    finally:
        _delete_incident(incident_id)


def test_two_operators_with_same_version_allow_only_one_command():
    incident_id = _create_incident('triage')
    try:
        results = _run_simultaneously(
            lambda: transition_incident(
                incident_id,
                'start_service',
                {'assigned_type': 'human', 'assigned_to': ACTOR_A['id']},
                ACTOR_A,
                1,
                f'ui210-assume:{uuid.uuid4()}',
            ),
            lambda: transition_incident(
                incident_id,
                'resolve',
                {
                    'resolution_code': 'operational_action_completed',
                    'resolution_notes': 'Ocorrência confirmada e tratada.',
                    'classification_reason': 'confirmed_risk',
                    'false_positive': False,
                },
                ACTOR_B,
                1,
                f'ui210-resolve:{uuid.uuid4()}',
            ),
        )

        successes = [result for result in results if isinstance(result, dict)]
        conflicts = [result for result in results if isinstance(result, IncidentConflict)]
        assert len(successes) == 1
        assert len(conflicts) == 1
        incident, timeline = _database_state(incident_id)
        assert incident['status'] in {'in_progress', 'resolved'}
        assert incident['version'] == 2
        assert len(timeline) == 1
        assert timeline[0]['entry_type'] == 'status_changed'
    finally:
        _delete_incident(incident_id)


def test_simultaneous_comment_retry_creates_one_timeline_entry():
    incident_id = _create_incident('triage')
    idempotency_key = f'ui210-comment:{uuid.uuid4()}'
    try:
        results = _run_simultaneously(
            lambda: add_incident_comment(
                incident_id, 'Contato iniciado com o proprietário.', ACTOR_A,
                1, idempotency_key,
            ),
            lambda: add_incident_comment(
                incident_id, 'Contato iniciado com o proprietário.', ACTOR_A,
                1, idempotency_key,
            ),
        )

        assert all(isinstance(result, dict) for result in results)
        assert sorted(result['idempotent_replay'] for result in results) == [False, True]
        incident, timeline = _database_state(incident_id)
        assert incident == {'status': 'triage', 'version': 2}
        assert timeline == [{
            'entry_type': 'comment',
            'idempotency_key': idempotency_key,
        }]
    finally:
        _delete_incident(incident_id)
