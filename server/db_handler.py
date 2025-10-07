import os
import json
import threading
import mysql.connector
from mysql.connector import pooling
from .env_loader import load_dotenv

# carrega .env (config/.env ou .env)
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('AITRACK_DB_HOST', 'camerascasas.no-ip.info'),
    'port': int(os.getenv('AITRACK_DB_PORT', '3307')),
    'user': os.getenv('AITRACK_DB_USER', 'scadabr'),
    'password': os.getenv('AITRACK_DB_PASSWORD', 'scadabr'),
    'database': os.getenv('AITRACK_DB_NAME', 'tracker'),
}

try:
    cnx_pool = pooling.MySQLConnectionPool(pool_name="aitrack_pool", pool_size=20, **DB_CONFIG)
except mysql.connector.Error as err:
    print(f"ERRO: Falha ao criar o pool de conexões: {err}")
    cnx_pool = None

# Modo alternativo de armazenamento para testes locais sem MySQL
USE_FILE_STORAGE = os.getenv("AITRACK_USE_FILE_STORAGE", "0") == "1"
FILE_STORAGE_PATH = os.getenv("AITRACK_FILE_PATH", "positions_log.jsonl")
_file_lock = threading.Lock()

def get_or_create_vehicle(cursor, device_id):
    """
    Verifica se um veículo existe. Se não, cria um.
    NUNCA usa IP:porta como ID (porta é efêmera e destrói continuidade).
    Para pacotes anônimos (Maxtrack real), consolidar em 'MAXTRACK-ANON'.
    """
    search_key = device_id if device_id else "MAXTRACK-ANON"
    cursor.execute("SELECT VEICOD FROM veiculos WHERE VEI_DEVICE_ID = %s", (search_key,))
    result = cursor.fetchone()

    if result:
        return result['VEICOD']
    else:
        placa = (search_key or "ANON")[:10]
        print(f"AVISO: Dispositivo com ID '{search_key}' não encontrado. Criando novo veículo com placa '{placa}'...")
        insert_sql = "INSERT INTO veiculos (VEIPLACA, VEI_DEVICE_ID) VALUES (%s, %s)"
        cursor.execute(insert_sql, (placa, search_key))
        return cursor.lastrowid

def _save_location_file(data):
    """Armazena posição em arquivo JSONL (modo teste local)."""
    record = {
        "device_id": data.get("device_id") or "MAXTRACK-ANON",
        "protocol": data.get("protocol"),
        "timestamp": data.get("timestamp"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "speed": data.get("speed"),
    }
    with _file_lock:
        with open(FILE_STORAGE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def save_location(data, addr):
    """Salva um ponto de localização, criando o veículo se necessário.
    Em modo arquivo, ignora MySQL e apenas persiste em JSONL.
    """
    if USE_FILE_STORAGE:
        _save_location_file(data)
        return

    if not cnx_pool:
        print("ERRO CRÍTICO: Pool de conexões não está disponível.")
        return

    conn = None
    try:
        conn = cnx_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        device_id = data.get('device_id')
        fk_veicod = get_or_create_vehicle(cursor, device_id)

        if not fk_veicod:
            print(f"ERRO: Não foi possível obter um ID de veículo para os dados: {data}")
            return

        lon = data.get('longitude')
        lat = data.get('latitude')
        timestamp = data.get('timestamp')
        speed = data.get('speed')
        altitude = data.get('altitude')
        heading = data.get('heading')
        orient_str = str(int(round(heading))) if heading is not None else None

        sql = """INSERT INTO localizacao (FK_VEICOD, LOCLATLONG, DATAHORA, VELATU, ALTITUDE, ORIENT)
                 VALUES (%s, ST_PointFromText('POINT(%s %s)'), %s, %s, %s, %s)"""
        
        cursor.execute(sql, (fk_veicod, lon, lat, timestamp, speed, altitude, orient_str))
        conn.commit()
        print(f"SUCESSO: Posição salva para o veículo FK_VEICOD={fk_veicod}.")

    except mysql.connector.Error as err:
        print(f"ERRO de Banco de Dados: {err}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
