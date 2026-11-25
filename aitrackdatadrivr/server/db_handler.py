import os
import json
import logging
import threading
import mysql.connector
from mysql.connector import pooling
from datetime import datetime
from .env_loader import load_dotenv
from .db_config import database_config
from . import behavioral_engine
from . import geofence_engine
from . import sensor_db
from . import route_detection_db


LOGGER = logging.getLogger(__name__)

# carrega .env (config/.env ou .env)
load_dotenv()

DB_CONFIG = database_config()

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


def _persist_sensor_readings(conn, cursor, fk_veicod, location_id, data):
    """Confirma a trilha de sensores sem desfazer a posição já persistida."""
    try:
        inserted = sensor_db.persist_tracker_readings(
            cursor,
            tracker_vehicle_id=fk_veicod,
            location_id=location_id,
            data=data,
            received_at=datetime.now(),
        )
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        LOGGER.exception('Falha ao persistir sensores do veículo Tracker %s', fk_veicod)
        return 0

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
        location_id = cursor.lastrowid
        conn.commit()
        print(f"SUCESSO: Posição salva para o veículo FK_VEICOD={fk_veicod}.")

        # Leituras normalizadas são derivadas apenas de capacidades confirmadas.
        # Uma falha aqui não pode invalidar a posição Tracker já confirmada.
        _persist_sensor_readings(conn, cursor, fk_veicod, location_id, data)

        # ============================================
        # BEHAVIORAL ENGINE: Detecta eventos
        # ============================================
        try:
            device_id_for_engine = device_id if device_id else f"FK-{fk_veicod}"

            # Prepara dados para o behavioral engine
            position_data = {
                'lat': lat,
                'lon': lon,
                'speed': speed if speed is not None else 0,
                'heading': heading if heading is not None else 0,
                'timestamp': timestamp if isinstance(timestamp, datetime) else datetime.now()
            }

            # Adiciona ao histórico e detecta eventos
            behavioral_engine.add_position(device_id_for_engine, position_data)

            # Obtém score atual
            current_score = behavioral_engine.get_vehicle_score(device_id_for_engine)
            print(f"   └─ Behavioral Score: {current_score}/100")

        except Exception as behavioral_err:
            print(f"   └─ AVISO: Erro no behavioral engine: {behavioral_err}")

        # Cerca eletrônica usa a mesma posição já persistida, mas falha isolada
        # nunca interrompe a ingestão principal do rastreador.
        try:
            geofence_engine.evaluate_tracker_position(
                device_id=device_id,
                vehicle_id=fk_veicod,
                longitude=lon,
                latitude=lat,
                observed_at=timestamp,
                accuracy_m=data.get('accuracy'),
                received_at=datetime.now(),
                external_position_id=location_id,
            )
        except Exception:
            LOGGER.exception('Falha ao avaliar cercas para veículo Tracker %s', fk_veicod)
        try:
            route_detection_db.evaluate_tracker_position(
                device_id=device_id,legacy_vehicle_id=fk_veicod,longitude=lon,latitude=lat,
                speed_kmh=speed or 0,observed_at=timestamp,accuracy_m=data.get('accuracy'),
                external_position_id=location_id,
            )
        except Exception:
            LOGGER.exception('Falha ao avaliar rota para veículo Tracker %s',fk_veicod)

    except mysql.connector.Error as err:
        print(f"ERRO de Banco de Dados: {err}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
