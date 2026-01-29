import socket
from concurrent.futures import ThreadPoolExecutor
from .protocol_parsers import parse_data
from .db_handler import save_location

HOST = '0.0.0.0'
PORT = 9000
MAX_WORKERS = 20

def handle_connection(conn, addr):
    """Processa uma única conexão, recebe um único pacote e fecha."""
    try:
        conn.settimeout(10.0)
        data = conn.recv(1024)
        if not data:
            return

        parsed_data = parse_data(data)
        if parsed_data:
            # Passa o endereço da conexão para ser usado como ID de fallback
            # OBS: save_location ignora addr para identificação (não usar IP:porta como ID)
            save_location(parsed_data, addr)

    except socket.timeout:
        print(f"AVISO: Timeout na conexão de {addr}. Nenhum dado recebido.")
    except Exception as e:
        print(f"ERRO em handle_connection para {addr}: {e}")
    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor (versão reconstruída final) escutando em {HOST}:{PORT}")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while True:
                try:
                    conn, addr = s.accept()
                    executor.submit(handle_connection, conn, addr)
                except Exception as e:
                    print(f"ERRO no loop principal do servidor: {e}")
