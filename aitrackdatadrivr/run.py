from threading import Thread
import time

# Importa a aplicação Flask e o iniciador do servidor de socket
from server.api import app
from server.behavioral_engine import restore_persisted_state
from server.socket_server import start_server
from server.dirijabem_geofence_ingestor import run_forever as run_dirijabem_geofence_ingestor
from server.geofence_incident_worker import run_forever as run_geofence_incident_worker
from server.offline_detector import run_forever as run_offline_detector
from server.device_command_db import run_timeout_worker
from dirijabem_simulator import get_replay_manager

def run_socket_server():
    """Função alvo para a thread do servidor de socket."""
    print("Iniciando o Servidor de Socket AITrack...")
    start_server()

def run_api_server():
    """Função alvo para a thread do servidor da API Flask."""
    print("Iniciando o Servidor da API Flask em http://0.0.0.0:5009...")
    app.run(host='0.0.0.0', port=5009, debug=False, use_reloader=False)

def run_dirijabem_simulator():
    """Função alvo para inicializar o simulador Dirijabem."""
    print("Iniciando o Simulador Dirijabem...")
    manager = get_replay_manager()
    print("Simulador Dirijabem pronto e aguardando requisições...")
    # Mantém a thread viva
    while True:
        time.sleep(1)

if __name__ == "__main__":
    restore_result = restore_persisted_state()
    print(
        "Estado comportamental: "
        f"{restore_result.get('scores', 0)} scores e "
        f"{restore_result.get('events', 0)} eventos restaurados."
    )

    # Cria as threads para cada servidor
    socket_thread = Thread(target=run_socket_server, daemon=True)
    api_thread = Thread(target=run_api_server, daemon=True)
    dirijabem_thread = Thread(target=run_dirijabem_simulator, daemon=True)
    dirijabem_ingestor_thread = Thread(
        target=run_dirijabem_geofence_ingestor,
        daemon=True,
    )
    geofence_incident_thread = Thread(
        target=run_geofence_incident_worker,
        daemon=True,
    )
    offline_detector_thread = Thread(target=run_offline_detector, daemon=True)
    command_timeout_thread = Thread(target=run_timeout_worker, daemon=True)

    print("Iniciando todos os serviços AITrack + Dirijabem...")

    # Inicia as threads
    socket_thread.start()
    api_thread.start()
    dirijabem_thread.start()
    dirijabem_ingestor_thread.start()
    geofence_incident_thread.start()
    offline_detector_thread.start()
    command_timeout_thread.start()

    try:
        # Mantém o processo principal vivo, esperando que as threads filhas terminem
        # (o que, em um servidor, geralmente não acontece a menos que haja um erro ou interrupção)
        while True:
            time.sleep(1)
            if not socket_thread.is_alive():
                print("ERRO: A thread do servidor de socket foi encerrada inesperadamente.")
                break
            if not api_thread.is_alive():
                print("ERRO: A thread do servidor da API foi encerrada inesperadamente.")
                break
            if not dirijabem_thread.is_alive():
                print("ERRO: A thread do simulador Dirijabem foi encerrada inesperadamente.")
                break
            if not dirijabem_ingestor_thread.is_alive():
                print("ERRO: O ingestor de cercas Dirijabem foi encerrado inesperadamente.")
                break
            if not geofence_incident_thread.is_alive():
                print("ERRO: O worker de incidentes de cerca foi encerrado inesperadamente.")
                break
            if not offline_detector_thread.is_alive():
                print("ERRO: A thread do detector offline foi encerrada inesperadamente.")
                break
            if not command_timeout_thread.is_alive():
                print("ERRO: A thread de timeout de comandos foi encerrada inesperadamente.")
                break

    except KeyboardInterrupt:
        print("\nRecebido sinal de interrupção. Encerrando os servidores...")

    # Espera as threads terminarem (elas são daemon então vão parar com o programa)
    socket_thread.join(timeout=2)
    api_thread.join(timeout=2)
    dirijabem_thread.join(timeout=2)
    dirijabem_ingestor_thread.join(timeout=2)
    geofence_incident_thread.join(timeout=2)
    offline_detector_thread.join(timeout=2)
    command_timeout_thread.join(timeout=2)

    print("Todos os serviços foram encerrados.")
