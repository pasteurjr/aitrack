from threading import Thread
import time

# Importa a aplicação Flask e o iniciador do servidor de socket
from server.api import app
from server.socket_server import start_server
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
    # Cria as threads para cada servidor
    socket_thread = Thread(target=run_socket_server, daemon=True)
    api_thread = Thread(target=run_api_server, daemon=True)
    dirijabem_thread = Thread(target=run_dirijabem_simulator, daemon=True)

    print("Iniciando todos os serviços AITrack + Dirijabem...")

    # Inicia as threads
    socket_thread.start()
    api_thread.start()
    dirijabem_thread.start()

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

    except KeyboardInterrupt:
        print("\nRecebido sinal de interrupção. Encerrando os servidores...")

    # Espera as threads terminarem (elas são daemon então vão parar com o programa)
    socket_thread.join(timeout=2)
    api_thread.join(timeout=2)
    dirijabem_thread.join(timeout=2)

    print("Todos os serviços foram encerrados.")
