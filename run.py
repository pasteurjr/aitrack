from multiprocessing import Process
import time

# Importa a aplicação Flask e o iniciador do servidor de socket
from server.api import app
from server.socket_server import start_server

def run_socket_server():
    """Função alvo para o processo do servidor de socket."""
    print("Iniciando o Servidor de Socket AITrack...")
    start_server()

def run_api_server():
    """Função alvo para o processo do servidor da API Flask."""
    print("Iniciando o Servidor da API Flask em http://0.0.0.0:5009...")
    # Usar debug=False em produção ou ao rodar com multiprocessing para evitar problemas
    app.run(host='0.0.0.0', port=5009, debug=False)

if __name__ == "__main__":
    # Cria os processos para cada servidor
    socket_process = Process(target=run_socket_server)
    api_process = Process(target=run_api_server)

    print("Iniciando todos os serviços AITrack...")

    # Inicia os processos
    socket_process.start()
    api_process.start()

    try:
        # Mantém o processo principal vivo, esperando que os processos filhos terminem
        # (o que, em um servidor, geralmente não acontece a menos que haja um erro ou interrupção)
        while True:
            time.sleep(1)
            if not socket_process.is_alive():
                print("ERRO: O processo do servidor de socket foi encerrado inesperadamente.")
                api_process.terminate() # Termina o processo da API também
                break
            if not api_process.is_alive():
                print("ERRO: O processo do servidor da API foi encerrado inesperadamente.")
                socket_process.terminate() # Termina o processo do socket também
                break

    except KeyboardInterrupt:
        print("\nRecebido sinal de interrupção. Encerrando os servidores...")
        socket_process.terminate()
        api_process.terminate()

    # Espera os processos terminarem de fato
    socket_process.join()
    api_process.join()

    print("Todos os serviços foram encerrados.")
