"""
Behavioral Engine - DataDrivr Integration
Detecta eventos comportamentais e calcula scores de direção
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import deque
import os
import logging
import threading
import mysql.connector
import json
import uuid

from .incident_correlator import correlate_episode

logger = logging.getLogger(__name__)

# Histórico de posições por veículo (últimas 5)
vehicle_history: Dict[str, deque] = {}

# Scores por veículo
vehicle_scores: Dict[str, float] = {}

# Eventos detectados
vehicle_events: List[Dict] = []

# Estado dos detectores por veículo. Episódios impedem que uma condição
# contínua gere um evento novo a cada pacote recebido.
vehicle_detector_state: Dict[str, Dict] = {}
_state_lock = threading.RLock()

# Thresholds de detecção
# Os limites são aceleração/desaceleração física. A janela é calculada pelo
# timestamp das amostras; nunca assumimos que cada pacote representa 1 segundo.
HARSH_ACCEL_THRESHOLD_MS2 = 15.0 / 3.6 / 3.0  # equivalente a 15 km/h em 3 s
HARSH_BRAKE_THRESHOLD_MS2 = 20.0 / 3.6 / 3.0  # equivalente a 20 km/h em 3 s
SPEEDING_THRESHOLD = 80.0      # km/h
SPEEDING_RELEASE_THRESHOLD = 75.0  # km/h; histerese para encerrar o episódio
SHARP_TURN_THRESHOLD_DEG_PER_SEC = 45.0 / 5.0  # equivalente a 45 graus em 5 s
DETECTOR_RELEASE_RATIO = 0.6
DETECTOR_COOLDOWN_SECONDS = float(os.getenv('AITRACK_DETECTOR_COOLDOWN_SECONDS', '30'))

MAX_HISTORY_SIZE = 5
INITIAL_SCORE = 100.0
SCORE_WINDOW_SECONDS = 60 * 60


def _timestamp_seconds(value) -> Optional[float]:
    """Converte timestamps aceitos pelo Tracker em segundos desde epoch."""
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        except ValueError:
            return None
    return None


def _elapsed_seconds(previous: Dict, current: Dict) -> Optional[float]:
    """Retorna o intervalo positivo entre duas posições, ou None se inválido."""
    previous_ts = _timestamp_seconds(previous.get('timestamp'))
    current_ts = _timestamp_seconds(current.get('timestamp'))
    if previous_ts is None or current_ts is None or current_ts <= previous_ts:
        return None
    return current_ts - previous_ts


def _heading_delta(previous_heading: float, current_heading: float) -> float:
    """Calcula a menor variação angular, inclusive na passagem 359→0."""
    change = abs(current_heading - previous_heading) % 360
    return min(change, 360 - change)


def _event_timestamp(current: Dict):
    value = current['timestamp']
    return value.isoformat() if isinstance(value, datetime) else value


def _episode_id(device_id: str, event_type: str, timestamp) -> str:
    """Gera identidade determinística para permitir deduplicação posterior."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aitrack:{device_id}:{event_type}:{timestamp}"))


def _detect_speeding_episode(
    device_id: str,
    current: Dict,
    detector_state: Dict,
) -> Optional[Dict]:
    """Emite somente o início de cada episódio contínuo de velocidade."""
    state = detector_state.setdefault('speeding', {'active': False, 'episode_id': None})
    speed = float(current.get('speed') or 0)

    if speed < SPEEDING_RELEASE_THRESHOLD:
        state['active'] = False
        state['episode_id'] = None
        return None

    if speed <= SPEEDING_THRESHOLD or state['active']:
        return None

    timestamp = _event_timestamp(current)
    episode_id = _episode_id(device_id, 'speeding', timestamp)
    state['active'] = True
    state['episode_id'] = episode_id
    excess = speed - SPEEDING_THRESHOLD
    return {
        'device_id': device_id,
        'type': 'speeding',
        'lat': current['lat'],
        'lon': current['lon'],
        'timestamp': timestamp,
        'severity': 'critical' if excess > 30 else 'high',
        'speed': speed,
        'speed_limit': SPEEDING_THRESHOLD,
        'excess': excess,
        'episode_id': episode_id,
        'episode_state': 'started',
        'icon': '🚨'
    }


def _detector_episode_gate(
    device_id: str,
    event_type: str,
    timestamp,
    condition_active: bool,
    condition_released: bool,
    detector_state: Dict,
) -> Optional[str]:
    """Aplica histerese e cooldown aos detectores de eventos transitórios."""
    state = detector_state.setdefault(event_type, {
        'active': False,
        'last_emitted_at': None,
        'episode_id': None,
    })

    if condition_released:
        state['active'] = False
        state['episode_id'] = None
        return None
    if not condition_active or state['active']:
        return None

    state['active'] = True
    timestamp_seconds = _timestamp_seconds(timestamp)
    last_emitted_at = state.get('last_emitted_at')
    if (
        timestamp_seconds is not None
        and last_emitted_at is not None
        and timestamp_seconds - last_emitted_at < DETECTOR_COOLDOWN_SECONDS
    ):
        return None

    episode_id = _episode_id(device_id, event_type, timestamp)
    state['episode_id'] = episode_id
    state['last_emitted_at'] = timestamp_seconds
    return episode_id

# Database configuration for event persistence
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}


def save_event_to_db(
    event: Dict,
    veicod: int,
    score_after: Optional[float] = None,
    events_in_window: int = 0,
):
    """
    Salva evento no banco de dados para persistência

    Args:
        event: Evento detectado com type, device_id, timestamp, etc
        veicod: VEICOD do veículo no banco de dados
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Buscar tipo_evento_id pelo código
        cursor.execute("SELECT id FROM tipo_evento WHERE codigo = %s", (event['type'],))
        tipo_result = cursor.fetchone()

        if not tipo_result:
            # Tipo não existe no catálogo, skip
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
        persisted_event_id = cursor.lastrowid

        # O evento e seu incidente são gravados na mesma transação. Ausência de
        # identidade unificada é tratada pelo correlacionador sem perder o evento.
        correlation = correlate_episode(
            cursor,
            event,
            tracker_event_id=persisted_event_id,
            score_after=score_after,
        )

        if score_after is not None:
            cursor.execute("""
                INSERT INTO tracker.behavioral_scores
                    (device_id, veicod, score, janela_minutos,
                     eventos_na_janela, calculado_em)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    veicod = VALUES(veicod),
                    score = VALUES(score),
                    janela_minutos = VALUES(janela_minutos),
                    eventos_na_janela = VALUES(eventos_na_janela),
                    calculado_em = VALUES(calculado_em)
            """, (
                event['device_id'],
                veicod,
                score_after,
                SCORE_WINDOW_SECONDS // 60,
                events_in_window,
                datetime.now(),
            ))

        conn.commit()
        event['_persisted_event_id'] = persisted_event_id
        event['_incident_id'] = correlation.get('incident_id')

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Erro persistindo evento e score: %s", e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _merge_persisted_state(score_rows: List[Dict], event_rows: List[Dict]) -> Dict:
    """Reidrata o estado essencial sem executar I/O; usada no startup e testes."""
    with _state_lock:
        for row in score_rows:
            device_id = row['device_id']
            init_vehicle(device_id)
            vehicle_scores[device_id] = float(row['score'])

        loaded_event_ids = {
            event.get('_persisted_event_id') for event in vehicle_events
            if event.get('_persisted_event_id') is not None
        }
        loaded = 0
        for row in event_rows:
            if row.get('id') in loaded_event_ids:
                continue
            device_id = row['device_id']
            init_vehicle(device_id)
            extras = row.get('dados_adicionais') or {}
            if isinstance(extras, str):
                try:
                    extras = json.loads(extras)
                except json.JSONDecodeError:
                    extras = {}
            timestamp = row['timestamp']
            timestamp_iso = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
            event = {
                'device_id': device_id,
                'type': row['type'],
                'lat': row.get('lat'),
                'lon': row.get('lon'),
                'timestamp': timestamp_iso,
                'severity': row.get('severity', 'medium'),
                'speed': row.get('speed'),
                '_persisted_event_id': row.get('id'),
                **extras,
            }
            vehicle_events.append(event)
            loaded_event_ids.add(row.get('id'))
            loaded += 1

            state = vehicle_detector_state[device_id].setdefault(row['type'], {})
            state['active'] = True
            state['episode_id'] = event.get('episode_id')
            if row['type'] != 'speeding':
                state['last_emitted_at'] = _timestamp_seconds(timestamp_iso)

        for device_id in vehicle_scores:
            vehicle_scores[device_id] = calculate_vehicle_score(device_id)

    return {'scores': len(score_rows), 'events': loaded}


def restore_persisted_state() -> Dict:
    """Restaura snapshots e eventos da janela ativa após reinício do backend."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT device_id, score
            FROM tracker.behavioral_scores
            ORDER BY atualizado_em DESC
            LIMIT 100000
        """)
        score_rows = cursor.fetchall()
        cutoff = datetime.now() - timedelta(seconds=SCORE_WINDOW_SECONDS)
        cursor.execute("""
            SELECT e.id, e.device_id, te.codigo AS type,
                   e.timestamp, e.latitude AS lat, e.longitude AS lon,
                   e.velocidade AS speed, e.severidade AS severity,
                   e.dados_adicionais
            FROM tracker.eventos e
            JOIN tracker.tipo_evento te ON te.id = e.tipo_evento_id
            WHERE e.timestamp >= %s AND e.device_id IS NOT NULL
            ORDER BY e.timestamp ASC
            LIMIT 20000
        """, (cutoff,))
        result = _merge_persisted_state(score_rows, cursor.fetchall())
        logger.info(
            "Estado comportamental restaurado: %s scores, %s eventos",
            result['scores'],
            result['events'],
        )
        return result
    except Exception as exc:
        logger.warning("Estado comportamental persistido indisponível: %s", exc)
        return {'scores': 0, 'events': 0, 'error': str(exc)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
        vehicle_detector_state[device_id] = {}


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
    events: List[Dict] = []
    with _state_lock:
        init_vehicle(device_id)
        history = vehicle_history[device_id]
        history.append(data)

        # Precisa de pelo menos 2 posições para detectar eventos
        if len(history) >= 2:
            events = detect_events(
                device_id,
                data,
                history,
                vehicle_detector_state[device_id],
            )
            for event in events:
                vehicle_events.append(event)
            score_after = calculate_vehicle_score(device_id)
            vehicle_scores[device_id] = score_after
            events_in_window = _count_events_in_score_window(device_id)

    # I/O não ocorre sob o lock do estado do motor.
    if events:
        veicod = get_veicod_from_device_id(device_id)
        if veicod:
            for event in events:
                save_event_to_db(event, veicod, score_after, events_in_window)


def detect_events(
    device_id: str,
    current: Dict,
    history: deque,
    detector_state: Optional[Dict] = None,
) -> List[Dict]:
    """
    Detecta eventos comportamentais comparando posição atual com histórico

    Returns:
        Lista de eventos detectados
    """
    events = []
    detector_state = detector_state if detector_state is not None else {}

    # 1. ACELERAÇÃO BRUSCA: compara a aceleração real, não a quantidade de
    # pacotes. Isso evita classificar incorretamente frequências diferentes.
    if len(history) >= 3:
        reference = list(history)[-3]
        speed_3s_ago = reference['speed']
        speed_now = current['speed']
        speed_delta = speed_now - speed_3s_ago
        elapsed = _elapsed_seconds(reference, current)
        acceleration = speed_delta / 3.6 / elapsed if elapsed else None
        episode_id = _detector_episode_gate(
            device_id,
            'harsh_accel',
            current['timestamp'],
            acceleration is not None and acceleration > HARSH_ACCEL_THRESHOLD_MS2,
            acceleration is not None and acceleration <= HARSH_ACCEL_THRESHOLD_MS2 * DETECTOR_RELEASE_RATIO,
            detector_state,
        )

        if episode_id:
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
                'elapsed_seconds': round(elapsed, 3),
                'acceleration_ms2': round(acceleration, 2),
                'episode_id': episode_id,
                'episode_state': 'started',
                'icon': '⚡'
            })

    # 2. FRENAGEM BRUSCA
    if len(history) >= 3:
        reference = list(history)[-3]
        speed_3s_ago = reference['speed']
        speed_now = current['speed']
        speed_delta = speed_3s_ago - speed_now  # invertido para desaceleração
        elapsed = _elapsed_seconds(reference, current)
        deceleration = speed_delta / 3.6 / elapsed if elapsed else None
        episode_id = _detector_episode_gate(
            device_id,
            'harsh_brake',
            current['timestamp'],
            deceleration is not None and deceleration > HARSH_BRAKE_THRESHOLD_MS2,
            deceleration is not None and deceleration <= HARSH_BRAKE_THRESHOLD_MS2 * DETECTOR_RELEASE_RATIO,
            detector_state,
        )

        if episode_id:
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
                'elapsed_seconds': round(elapsed, 3),
                'deceleration_ms2': round(deceleration, 2),
                'episode_id': episode_id,
                'episode_state': 'started',
                'icon': '🛑'
            })

    # 3. EXCESSO DE VELOCIDADE: um evento por episódio. O detector só rearma
    # abaixo de 75 km/h, evitando oscilações na fronteira de 80 km/h.
    speeding_event = _detect_speeding_episode(device_id, current, detector_state)
    if speeding_event:
        events.append(speeding_event)

    # 4. CURVA BRUSCA: a mudança angular também depende do tempo real.
    if len(history) >= 5:
        reference = list(history)[-5]
        heading_5s_ago = reference['heading']
        heading_now = current['heading']
        elapsed = _elapsed_seconds(reference, current)
        heading_change = _heading_delta(heading_5s_ago, heading_now)
        turn_rate = heading_change / elapsed if elapsed else None
        speed = current['speed']
        episode_id = _detector_episode_gate(
            device_id,
            'sharp_turn',
            current['timestamp'],
            turn_rate is not None and turn_rate > SHARP_TURN_THRESHOLD_DEG_PER_SEC and speed > 30,
            turn_rate is not None and turn_rate <= SHARP_TURN_THRESHOLD_DEG_PER_SEC * DETECTOR_RELEASE_RATIO,
            detector_state,
        )

        if episode_id:
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
                'elapsed_seconds': round(elapsed, 3),
                'turn_rate_deg_per_sec': round(turn_rate, 2),
                'speed': speed,
                'episode_id': episode_id,
                'episode_state': 'started',
                'icon': '↪️'
            })

    return events


def update_score(device_id: str, event: Dict):
    """
    Recalcula o score usando os eventos ativos da última hora.

    O score é uma janela deslizante: quando um evento envelhece, sua
    penalidade deixa de participar do cálculo e o veículo se recupera.
    """
    vehicle_scores[device_id] = calculate_vehicle_score(device_id)


def _dedupe_episode_events(events) -> List[Dict]:
    """Remove somente duplicatas com identidade explícita de episódio."""
    unique = []
    seen_episode_ids = set()
    for event in events:
        episode_id = event.get('episode_id')
        if episode_id:
            if episode_id in seen_episode_ids:
                continue
            seen_episode_ids.add(episode_id)
        unique.append(event)
    return unique


def _count_events_in_score_window(
    device_id: str,
    now: Optional[datetime] = None,
) -> int:
    now_seconds = _timestamp_seconds(now or datetime.now(timezone.utc))
    active_events = (
        event for event in vehicle_events
        if event.get('device_id') == device_id
        and (event_seconds := _timestamp_seconds(event.get('timestamp'))) is not None
        and 0 <= now_seconds - event_seconds <= SCORE_WINDOW_SECONDS
    )
    return len(_dedupe_episode_events(active_events))


def calculate_vehicle_score(device_id: str, now: Optional[datetime] = None) -> float:
    """Calcula o score sem depender de quantas posições foram recebidas."""
    now_seconds = _timestamp_seconds(now or datetime.now(timezone.utc))
    penalties = {
        'harsh_accel': 2.0,
        'harsh_brake': 3.0,
        'speeding': 1.0,
        'sharp_turn': 2.0,
    }
    total_penalty = 0.0

    device_events = _dedupe_episode_events(
        event for event in vehicle_events
        if event.get('device_id') == device_id
    )
    for event in device_events:
        event_seconds = _timestamp_seconds(event.get('timestamp'))
        if event_seconds is None or event_seconds > now_seconds:
            continue
        age = now_seconds - event_seconds
        if age <= SCORE_WINDOW_SECONDS:
            penalty = penalties.get(event.get('type'), 1.0)
            if event.get('severity') == 'high':
                penalty *= 1.5
            elif event.get('severity') == 'critical':
                penalty *= 2
            total_penalty += penalty

    return round(max(0.0, min(100.0, INITIAL_SCORE - total_penalty)), 1)


def get_vehicle_score(device_id: str) -> float:
    """Retorna score atual do veículo"""
    score = calculate_vehicle_score(device_id)
    vehicle_scores[device_id] = score
    return score


def get_all_scores() -> Dict[str, float]:
    """Retorna todos os scores"""
    for device_id in list(vehicle_scores):
        vehicle_scores[device_id] = calculate_vehicle_score(device_id)
    return vehicle_scores.copy()


def get_recent_events(limit: int = 50, device_id: Optional[str] = None) -> List[Dict]:
    """
    Retorna eventos recentes

    Args:
        limit: Número máximo de eventos
        device_id: Filtrar por veículo específico (opcional)
    """
    events = list(vehicle_events)

    if device_id:
        events = [e for e in events if e['device_id'] == device_id]

    # Retorna os mais recentes primeiro
    episodes = _dedupe_episode_events(events)
    return list(reversed(episodes[-limit:]))


def get_fleet_stats(now: Optional[datetime] = None) -> Dict:
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

    scores = list(get_all_scores().items())
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

    reference_date = (now or datetime.now()).date()
    episodes_today = _dedupe_episode_events(
        event for event in vehicle_events
        if (
            (event_seconds := _timestamp_seconds(event.get('timestamp'))) is not None
            and datetime.fromtimestamp(event_seconds).date() == reference_date
        )
    )

    return {
        'fleet_avg': round(fleet_avg, 1),
        'total_vehicles': len(vehicle_scores),
        'events_today': len(episodes_today),
        'top3': top3,
        'bottom3': bottom3
    }


def reset_all():
    """Limpa todos os dados (útil para testes)"""
    with _state_lock:
        vehicle_history.clear()
        vehicle_scores.clear()
        vehicle_events.clear()
        vehicle_detector_state.clear()
