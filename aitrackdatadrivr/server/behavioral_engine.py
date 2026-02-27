"""
Behavioral Engine - DataDrivr Integration
Detecta eventos comportamentais e calcula scores de direção
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque
import mysql.connector
import json

# Histórico de posições por veículo (últimas 5)
vehicle_history: Dict[str, deque] = {}

# Scores por veículo
vehicle_scores: Dict[str, float] = {}

# Eventos detectados
vehicle_events: List[Dict] = []

# Thresholds de detecção
HARSH_ACCEL_THRESHOLD = 15.0  # km/h em 3 segundos
HARSH_BRAKE_THRESHOLD = 20.0  # km/h em 3 segundos
SPEEDING_THRESHOLD = 80.0      # km/h
SHARP_TURN_THRESHOLD = 45.0    # graus em 5 segundos

MAX_HISTORY_SIZE = 5
INITIAL_SCORE = 85.0

# Database configuration for event persistence
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}


def save_event_to_db(event: Dict, veicod: int):
    """
    Salva evento no banco de dados para persistência

    Args:
        event: Evento detectado com type, device_id, timestamp, etc
        veicod: VEICOD do veículo no banco de dados
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Buscar tipo_evento_id pelo código
        cursor.execute("SELECT id FROM tipo_evento WHERE codigo = %s", (event['type'],))
        tipo_result = cursor.fetchone()

        if not tipo_result:
            # Tipo não existe no catálogo, skip
            cursor.close()
            conn.close()
            return

        tipo_evento_id = tipo_result['id']

        # Preparar dados adicionais (tudo que não é campo direto)
        dados_adicionais = {k: v for k, v in event.items()
                          if k not in ['device_id', 'type', 'lat', 'lon', 'timestamp', 'severity']}

        # Converter timestamp se necessário
        if isinstance(event['timestamp'], str):
            timestamp = datetime.fromisoformat(event['timestamp'])
        else:
            timestamp = event['timestamp']

        # Insert evento
        insert_sql = """
        INSERT INTO eventos (tipo_evento_id, veicod, device_id, timestamp,
                           latitude, longitude, velocidade, dados_adicionais, severidade)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_sql, (
            tipo_evento_id,
            veicod,
            event['device_id'],
            timestamp,
            event.get('lat'),
            event.get('lon'),
            event.get('speed', event.get('speed_after', 0)),
            json.dumps(dados_adicionais),
            event.get('severity', 'medium')
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        # Falha silenciosa - evento ainda fica in-memory
        print(f"[WARN] Erro salvando evento no banco: {e}")


def get_veicod_from_device_id(device_id: str) -> Optional[int]:
    """
    Busca VEICOD no banco de dados a partir do device_id

    Args:
        device_id: VEI_DEVICE_ID do veículo

    Returns:
        VEICOD ou None se não encontrado
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT VEICOD FROM veiculos WHERE VEI_DEVICE_ID = %s", (device_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result['VEICOD'] if result else None
    except Exception as e:
        print(f"[WARN] Erro buscando VEICOD: {e}")
        return None


def init_vehicle(device_id: str):
    """Inicializa histórico e score de um veículo"""
    if device_id not in vehicle_history:
        vehicle_history[device_id] = deque(maxlen=MAX_HISTORY_SIZE)
        vehicle_scores[device_id] = INITIAL_SCORE


def add_position(device_id: str, data: Dict):
    """
    Adiciona posição ao histórico e detecta eventos

    Args:
        device_id: ID do dispositivo/veículo
        data: {
            'lat': float,
            'lon': float,
            'speed': float,
            'heading': float,
            'timestamp': datetime
        }
    """
    init_vehicle(device_id)

    history = vehicle_history[device_id]
    history.append(data)

    # Precisa de pelo menos 2 posições para detectar eventos
    if len(history) >= 2:
        events = detect_events(device_id, data, history)

        for event in events:
            # Adiciona à lista global (mantém in-memory para performance)
            vehicle_events.append(event)

            # Atualiza score
            update_score(device_id, event)

            # NOVO: Salva no banco de dados para persistência
            veicod = get_veicod_from_device_id(device_id)
            if veicod:
                save_event_to_db(event, veicod)


def detect_events(device_id: str, current: Dict, history: deque) -> List[Dict]:
    """
    Detecta eventos comportamentais comparando posição atual com histórico

    Returns:
        Lista de eventos detectados
    """
    events = []

    # 1. ACELERAÇÃO BRUSCA
    if len(history) >= 3:
        speed_3s_ago = list(history)[-3]['speed']
        speed_now = current['speed']

        speed_delta = speed_now - speed_3s_ago

        if speed_delta > HARSH_ACCEL_THRESHOLD:
            acceleration = speed_delta / 3.6 / 3  # converte para m/s²
            events.append({
                'device_id': device_id,
                'type': 'harsh_accel',
                'lat': current['lat'],
                'lon': current['lon'],
                'timestamp': current['timestamp'].isoformat() if isinstance(current['timestamp'], datetime) else current['timestamp'],
                'severity': 'high' if speed_delta > 25 else 'medium',
                'speed_before': speed_3s_ago,
                'speed_after': speed_now,
                'delta': speed_delta,
                'acceleration_ms2': round(acceleration, 2),
                'icon': '⚡'
            })

    # 2. FRENAGEM BRUSCA
    if len(history) >= 3:
        speed_3s_ago = list(history)[-3]['speed']
        speed_now = current['speed']

        speed_delta = speed_3s_ago - speed_now  # invertido para desaceleração

        if speed_delta > HARSH_BRAKE_THRESHOLD:
            deceleration = speed_delta / 3.6 / 3  # converte para m/s²
            events.append({
                'device_id': device_id,
                'type': 'harsh_brake',
                'lat': current['lat'],
                'lon': current['lon'],
                'timestamp': current['timestamp'].isoformat() if isinstance(current['timestamp'], datetime) else current['timestamp'],
                'severity': 'high' if speed_delta > 30 else 'medium',
                'speed_before': speed_3s_ago,
                'speed_after': speed_now,
                'delta': speed_delta,
                'deceleration_ms2': round(deceleration, 2),
                'icon': '🛑'
            })

    # 3. EXCESSO DE VELOCIDADE
    if current['speed'] > SPEEDING_THRESHOLD:
        excess = current['speed'] - SPEEDING_THRESHOLD
        events.append({
            'device_id': device_id,
            'type': 'speeding',
            'lat': current['lat'],
            'lon': current['lon'],
            'timestamp': current['timestamp'].isoformat() if isinstance(current['timestamp'], datetime) else current['timestamp'],
            'severity': 'critical' if excess > 30 else 'high',
            'speed': current['speed'],
            'speed_limit': SPEEDING_THRESHOLD,
            'excess': excess,
            'icon': '🚨'
        })

    # 4. CURVA BRUSCA
    if len(history) >= 5:
        heading_5s_ago = list(history)[-5]['heading']
        heading_now = current['heading']

        # Calcula menor ângulo entre as direções
        heading_change = abs(heading_now - heading_5s_ago)
        if heading_change > 180:
            heading_change = 360 - heading_change

        speed = current['speed']

        if heading_change > SHARP_TURN_THRESHOLD and speed > 30:
            events.append({
                'device_id': device_id,
                'type': 'sharp_turn',
                'lat': current['lat'],
                'lon': current['lon'],
                'timestamp': current['timestamp'].isoformat() if isinstance(current['timestamp'], datetime) else current['timestamp'],
                'severity': 'high' if heading_change > 90 else 'medium',
                'heading_before': heading_5s_ago,
                'heading_after': heading_now,
                'heading_change': round(heading_change, 1),
                'speed': speed,
                'icon': '↪️'
            })

    return events


def update_score(device_id: str, event: Dict):
    """
    Atualiza score do veículo baseado em evento detectado
    Score vai de 0-100, começa em 85
    """
    current_score = vehicle_scores.get(device_id, INITIAL_SCORE)

    # Penalidades por tipo de evento
    penalties = {
        'harsh_accel': -2,
        'harsh_brake': -3,
        'speeding': -1,
        'sharp_turn': -2
    }

    # Aplica penalidade baseada na severidade
    penalty = penalties.get(event['type'], -1)
    if event.get('severity') == 'high':
        penalty *= 1.5
    elif event.get('severity') == 'critical':
        penalty *= 2

    # Score mínimo de 10 (motorista extremamente ruim mas ainda mensurável)
    new_score = max(10, min(100, current_score + penalty))
    vehicle_scores[device_id] = round(new_score, 1)


def get_vehicle_score(device_id: str) -> float:
    """Retorna score atual do veículo"""
    return vehicle_scores.get(device_id, INITIAL_SCORE)


def get_all_scores() -> Dict[str, float]:
    """Retorna todos os scores"""
    return vehicle_scores.copy()


def get_recent_events(limit: int = 50, device_id: Optional[str] = None) -> List[Dict]:
    """
    Retorna eventos recentes

    Args:
        limit: Número máximo de eventos
        device_id: Filtrar por veículo específico (opcional)
    """
    events = vehicle_events

    if device_id:
        events = [e for e in events if e['device_id'] == device_id]

    # Retorna os mais recentes primeiro
    return list(reversed(events[-limit:]))


def get_fleet_stats() -> Dict:
    """
    Calcula estatísticas da frota

    Returns:
        {
            'fleet_avg': float,
            'total_vehicles': int,
            'events_today': int,
            'top3': [...],
            'bottom3': [...]
        }
    """
    if not vehicle_scores:
        return {
            'fleet_avg': 0,
            'total_vehicles': 0,
            'events_today': 0,
            'top3': [],
            'bottom3': []
        }

    scores = list(vehicle_scores.items())
    fleet_avg = sum(s for _, s in scores) / len(scores)

    # Ordena por score
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    top3 = [
        {'device_id': device_id, 'score': score}
        for device_id, score in sorted_scores[:3]
    ]

    bottom3 = [
        {'device_id': device_id, 'score': score}
        for device_id, score in sorted_scores[-3:]
    ]

    return {
        'fleet_avg': round(fleet_avg, 1),
        'total_vehicles': len(vehicle_scores),
        'events_today': len(vehicle_events),
        'top3': top3,
        'bottom3': bottom3
    }


def reset_all():
    """Limpa todos os dados (útil para testes)"""
    vehicle_history.clear()
    vehicle_scores.clear()
    vehicle_events.clear()
