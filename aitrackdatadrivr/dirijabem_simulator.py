#!/usr/bin/env python3
"""
Dirijabem Trip Replay System
Replays real trips from dirijabem database point-by-point
"""

import json
import time
import random
import math
import mysql.connector
from datetime import datetime, timedelta
from threading import Thread, Lock
from pathlib import Path
from typing import List, Dict

# Configuration
SPEED_MULTIPLIER = 1  # 1 = real-time, 10 = 10x faster
ROUTES_FILE = 'config/dirijabem_routes.json'

# Database connection
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'dirijabem',
    'pool_name': 'dirijabem_pool',
    'pool_size': 5
}


# ==============================================================================
# SYNTHETIC DATA GENERATION - Driver Profiles and Route Generator
# ==============================================================================

class DriverProfile:
    """Perfis comportamentais realistas de motorista"""

    PROFILES = {
        'excellent': {
            'name': 'Excelente',
            'score_range': (85, 100),
            'speeding_probability': 0.05,      # 5% do tempo em excesso
            'harsh_accel_count': (0, 1),       # 0-1 acelerações bruscas
            'harsh_brake_count': (0, 1),       # 0-1 frenagens bruscas
            'sharp_turn_count': (0, 2),        # 0-2 curvas acentuadas
            'speed_excess_avg': 5,              # +5 km/h quando excede
            'aggression_level': 0.1,            # 10% agressivo
        },

        'good': {
            'name': 'Bom',
            'score_range': (70, 84),
            'speeding_probability': 0.15,
            'harsh_accel_count': (1, 2),
            'harsh_brake_count': (1, 2),
            'sharp_turn_count': (2, 4),
            'speed_excess_avg': 10,
            'aggression_level': 0.2,
        },

        'average': {
            'name': 'Médio',
            'score_range': (55, 69),
            'speeding_probability': 0.25,
            'harsh_accel_count': (2, 4),
            'harsh_brake_count': (2, 4),
            'sharp_turn_count': (3, 6),
            'speed_excess_avg': 15,
            'aggression_level': 0.35,
        },

        'poor': {
            'name': 'Ruim',
            'score_range': (40, 54),
            'speeding_probability': 0.40,
            'harsh_accel_count': (3, 6),
            'harsh_brake_count': (3, 6),
            'sharp_turn_count': (5, 10),
            'speed_excess_avg': 20,
            'aggression_level': 0.55,
        },

        'aggressive': {
            'name': 'Agressivo',
            'score_range': (20, 39),
            'speeding_probability': 0.60,
            'harsh_accel_count': (5, 10),
            'harsh_brake_count': (5, 10),
            'sharp_turn_count': (8, 15),
            'speed_excess_avg': 25,
            'aggression_level': 0.85,
        }
    }

    @staticmethod
    def get_random_profile():
        """Retorna perfil aleatório com distribuição realista"""
        rand = random.random()
        if rand < 0.15:
            return 'excellent'
        elif rand < 0.35:
            return 'good'
        elif rand < 0.65:
            return 'average'
        elif rand < 0.85:
            return 'poor'
        else:
            return 'aggressive'


class SyntheticRouteGenerator:
    """Gera rotas sintéticas REALISTAS para Belo Horizonte"""

    def __init__(self):
        # Bounds de Belo Horizonte
        self.LAT_MIN = -19.96
        self.LAT_MAX = -19.94
        self.LON_MIN = -43.93
        self.LON_MAX = -43.91

        # Parâmetros de realismo
        self.AVG_SPEED = 40  # km/h
        self.MAX_SPEED = 80  # km/h
        self.SPEED_LIMIT = 60  # Limite de velocidade
        self.POINT_INTERVAL = 1  # segundos

    def generate_route(self, duration_minutes=10, driver_profile='average'):
        """
        Gera uma rota sintética com pontos GPS e perfil comportamental

        Args:
            duration_minutes: Duração da viagem em minutos
            driver_profile: 'excellent', 'good', 'average', 'poor', 'aggressive'

        Returns: List[dict] com estrutura compatível com rotas reais
        """
        profile = DriverProfile.PROFILES[driver_profile]
        points = []
        num_points = duration_minutes * 60  # 1 ponto por segundo

        # Ponto inicial aleatório em Belo Horizonte
        current_lat = random.uniform(self.LAT_MIN, self.LAT_MAX)
        current_lon = random.uniform(self.LON_MIN, self.LON_MAX)
        current_heading = random.uniform(0, 360)  # Direção inicial aleatória
        current_speed = 0

        start_time = datetime.now()

        # Gerar trajetória ponto a ponto
        for i in range(num_points):
            # Calcular velocidade realista
            target_speed = self._get_target_speed(i, num_points, profile)
            current_speed = self._smooth_speed_change(current_speed, target_speed)

            # Calcular aceleração
            if i > 0:
                prev_speed = points[i-1]['VELATU']
                accel = (current_speed - prev_speed) / 3.6  # m/s²
            else:
                accel = 0

            # Calcular mudança de direção (curvas naturais)
            heading_change = random.gauss(0, 3)  # Pequenas variações naturais
            current_heading = (current_heading + heading_change) % 360

            # Calcular próxima posição baseado em velocidade e direção
            distance_m = (current_speed / 3.6)  # Distância em 1 segundo
            delta_lat = (distance_m / 111320) * math.cos(math.radians(current_heading))
            delta_lon = (distance_m / (111320 * math.cos(math.radians(current_lat))))

            current_lat += delta_lat
            current_lon += delta_lon

            # Manter dentro dos bounds
            current_lat = max(self.LAT_MIN, min(self.LAT_MAX, current_lat))
            current_lon = max(self.LON_MIN, min(self.LON_MAX, current_lon))

            points.append({
                'timestamp': (start_time + timedelta(seconds=i)).isoformat(),
                'lat': current_lat,
                'lon': current_lon,
                'speed': current_speed,
                'VELATU': current_speed,
                'ACELLINATU': accel,
                'VARDIRATU': abs(heading_change),
                'coords': (current_lon, current_lat)  # Formato MySQL: lon, lat
            })

        return points

    def _get_target_speed(self, point_index, total_points, profile):
        """Calcula velocidade alvo baseado no perfil do motorista"""
        # Fase de aceleração (primeiros 30s)
        if point_index < 30:
            return (point_index / 30) * self.AVG_SPEED

        # Fase de desaceleração (últimos 30s)
        elif point_index > total_points - 30:
            return ((total_points - point_index) / 30) * self.AVG_SPEED

        # Fase de cruzeiro (meio da viagem)
        else:
            base_speed = self.AVG_SPEED

            # Adicionar variação baseada no perfil
            variation = random.gauss(0, 5)
            target = base_speed + variation

            # Motoristas agressivos tendem a ir mais rápido
            if random.random() < profile['aggression_level']:
                target *= 1.2

            return min(target, self.MAX_SPEED)

    def _smooth_speed_change(self, current, target):
        """Suaviza mudanças de velocidade (realista)"""
        max_change = 5  # Máximo 5 km/h por segundo
        diff = target - current

        if abs(diff) <= max_change:
            return target
        else:
            return current + (max_change if diff > 0 else -max_change)

    def inject_realistic_events(self, points, driver_profile='average'):
        """
        Injeta eventos comportamentais CONTEXTUALIZADOS

        Esta é a grande melhoria: eventos têm contexto e são realistas!
        """
        profile = DriverProfile.PROFILES[driver_profile]

        # ==========================================
        # 1. EXCESSO DE VELOCIDADE (distribuído naturalmente)
        # ==========================================
        speeding_prob = profile['speeding_probability']
        speed_excess = profile['speed_excess_avg']

        for i in range(30, len(points) - 30):  # Não no início/fim
            if random.random() < speeding_prob:
                # Adicionar excesso gradual (não abrupto)
                excess = random.gauss(speed_excess, 3)
                points[i]['VELATU'] = min(
                    points[i]['VELATU'] + excess,
                    self.MAX_SPEED
                )
                points[i]['speed'] = points[i]['VELATU']

        # ==========================================
        # 2. CURVAS BRUSCAS (com contexto: freada antes)
        # ==========================================
        num_turns = random.randint(*profile['sharp_turn_count'])

        for _ in range(num_turns):
            idx = random.randint(60, len(points) - 60)

            # Curva brusca (45-90 graus)
            turn_angle = random.uniform(45, 90)
            points[idx]['VARDIRATU'] = turn_angle

            # CONTEXTO: Reduzir velocidade ANTES da curva (realista!)
            for j in range(idx - 5, idx):
                if j >= 0:
                    points[j]['VELATU'] *= 0.85  # Reduz 15%
                    points[j]['speed'] *= 0.85
                    if j == idx - 1:
                        points[j]['ACELLINATU'] = -2.5  # Freada moderada

            # CONTEXTO: Acelerar DEPOIS da curva
            for j in range(idx + 1, min(idx + 5, len(points))):
                points[j]['ACELLINATU'] = random.uniform(1.5, 2.5)

        # ==========================================
        # 3. ACELERAÇÕES BRUSCAS (contextualizadas)
        # ==========================================
        num_accels = random.randint(*profile['harsh_accel_count'])

        for _ in range(num_accels):
            idx = random.randint(60, len(points) - 60)

            # Aceleração brusca (>3.5 m/s²)
            harsh_accel = random.uniform(3.5, 5.5)
            points[idx]['ACELLINATU'] = harsh_accel

            # CONTEXTO: Aumentar velocidade nos próximos pontos
            base_speed = points[idx]['VELATU']
            for j in range(idx, min(idx + 6, len(points))):
                increment = (j - idx) * 7
                points[j]['VELATU'] = min(base_speed + increment, self.MAX_SPEED)
                points[j]['speed'] = points[j]['VELATU']

        # ==========================================
        # 4. FRENAGENS BRUSCAS (NOVO! Estava faltando)
        # ==========================================
        num_brakes = random.randint(*profile['harsh_brake_count'])

        for _ in range(num_brakes):
            idx = random.randint(60, len(points) - 60)

            # Frenagem brusca (<-3.5 m/s²)
            harsh_brake = random.uniform(-5.0, -3.5)
            points[idx]['ACELLINATU'] = harsh_brake

            # CONTEXTO: Reduzir velocidade drasticamente
            base_speed = points[idx]['VELATU']
            for j in range(idx, min(idx + 6, len(points))):
                decrement = (j - idx) * 10
                points[j]['VELATU'] = max(base_speed - decrement, 5)
                points[j]['speed'] = points[j]['VELATU']

        # ==========================================
        # 5. COMBOS REALISTAS (eventos correlacionados)
        # ==========================================
        # Combo 1: Excesso → Freada brusca → Curva → Aceleração
        if driver_profile in ['poor', 'aggressive'] and len(points) > 300:
            idx = random.randint(200, len(points) - 100)

            # Excesso de velocidade
            for j in range(idx - 20, idx):
                if j >= 0:
                    points[j]['VELATU'] = min(points[j]['VELATU'] * 1.3, self.MAX_SPEED)

            # Freada brusca (percebeu tarde!)
            points[idx]['ACELLINATU'] = -4.5
            points[idx]['VELATU'] *= 0.5

            # 2 segundos depois: Curva acentuada
            if idx + 2 < len(points):
                points[idx + 2]['VARDIRATU'] = 70

            # 4 segundos depois: Aceleração compensatória
            if idx + 5 < len(points):
                points[idx + 5]['ACELLINATU'] = 4.2
                points[idx + 5]['VELATU'] *= 1.4

        return points


class BehavioralMetricsCalculator:
    """Calcula métricas fuzzy logic do Dirijabem"""

    SPEED_LIMIT = 60  # km/h

    def calculate_metrics(self, points: List[dict]) -> dict:
        """
        Calcula todas as 12 métricas comportamentais

        Returns: {OST, OSA, OSP, SAM, SAA, BRP, BRM, BRA, GAM, GAA, GAP, GAN, SCORE}
        """
        if not points:
            return self._empty_metrics()

        metrics = {}

        # Over-speeding metrics
        metrics['OST'] = self._calculate_speeding_time(points)
        metrics['OSA'] = self._calculate_speeding_avg(points)
        metrics['OSP'] = self._calculate_speeding_peak(points)

        # Acceleration metrics
        metrics['SAM'], metrics['SAA'] = self._calculate_accel_events(points)
        metrics['GAM'], metrics['GAA'] = self._calculate_accel_per_km(points)
        metrics['GAP'], metrics['GAN'] = self._calculate_peak_accel(points)

        # Bearing/turning metrics
        metrics['BRP'] = self._calculate_max_bearing_change(points)
        metrics['BRM'], metrics['BRA'] = self._calculate_turn_events(points)

        # Score global (fuzzy logic)
        metrics['SCORE'] = self._calculate_fuzzy_score(metrics)

        return metrics

    def _empty_metrics(self):
        """Retorna métricas vazias"""
        return {
            'OST': 0, 'OSA': 0, 'OSP': 0,
            'SAM': 0, 'SAA': 0,
            'GAM': 0, 'GAA': 0, 'GAP': 0, 'GAN': 0,
            'BRP': 0, 'BRM': 0, 'BRA': 0,
            'SCORE': 100
        }

    def _calculate_speeding_time(self, points):
        """OST: Proporção de tempo em excesso de velocidade"""
        speeding_points = sum(1 for p in points if p.get('VELATU', 0) > self.SPEED_LIMIT)
        return speeding_points / len(points) if points else 0

    def _calculate_speeding_avg(self, points):
        """OSA: Média de excesso de velocidade"""
        excesses = [p['VELATU'] - self.SPEED_LIMIT for p in points
                   if p.get('VELATU', 0) > self.SPEED_LIMIT]
        return sum(excesses) / len(excesses) if excesses else 0

    def _calculate_speeding_peak(self, points):
        """OSP: Velocidade máxima registrada acima do limite"""
        speeds_over = [p['VELATU'] - self.SPEED_LIMIT for p in points
                      if p.get('VELATU', 0) > self.SPEED_LIMIT]
        return max(speeds_over) if speeds_over else 0

    def _calculate_accel_events(self, points):
        """SAM, SAA: Contagem e média de acelerações bruscas (>3.0 m/s²)"""
        harsh_accels = [p['ACELLINATU'] for p in points
                       if p.get('ACELLINATU', 0) > 3.0]
        sam = len(harsh_accels)
        saa = sum(harsh_accels) / len(harsh_accels) if harsh_accels else 0
        return sam, saa

    def _calculate_accel_per_km(self, points):
        """GAM, GAA: Acelerações por km e média"""
        # Calcular distância total (aproximada)
        total_distance_km = sum(p.get('VELATU', 0) for p in points) / 3600  # km

        harsh_accels = [p['ACELLINATU'] for p in points
                       if p.get('ACELLINATU', 0) > 3.0]

        gam = len(harsh_accels) / total_distance_km if total_distance_km > 0 else 0
        gaa = sum(harsh_accels) / len(harsh_accels) if harsh_accels else 0

        return gam, gaa

    def _calculate_peak_accel(self, points):
        """GAP, GAN: Picos de aceleração (positiva e negativa)"""
        accels = [p.get('ACELLINATU', 0) for p in points]
        gap = max(accels) if accels else 0
        gan = min(accels) if accels else 0
        return gap, gan

    def _calculate_max_bearing_change(self, points):
        """BRP: Maior mudança de direção"""
        bearing_changes = [p.get('VARDIRATU', 0) for p in points]
        return max(bearing_changes) if bearing_changes else 0

    def _calculate_turn_events(self, points):
        """BRM, BRA: Contagem e média de curvas acentuadas (>45°)"""
        sharp_turns = [p['VARDIRATU'] for p in points
                      if p.get('VARDIRATU', 0) > 45]
        brm = len(sharp_turns)
        bra = sum(sharp_turns) / len(sharp_turns) if sharp_turns else 0
        return brm, bra

    def _calculate_fuzzy_score(self, metrics):
        """
        Calcula score 0-100 usando lógica fuzzy simplificada
        Quanto MENOR o score, PIOR o motorista
        """
        score = 100.0

        # Penalidades por over-speeding
        score -= metrics['OST'] * 20  # Proporção de tempo em excesso
        score -= metrics['OSA'] * 0.5  # Média de excesso
        score -= metrics['OSP'] * 0.2  # Pico de excesso

        # Penalidades por acelerações bruscas
        score -= metrics['SAM'] * 2  # Contagem
        score -= metrics['SAA'] * 1.5  # Média

        # Penalidades por curvas acentuadas
        score -= metrics['BRM'] * 1  # Contagem
        score -= metrics['BRA'] * 0.3  # Média

        # Penalidades por acelerações extremas
        if metrics['GAP'] > 4.0:
            score -= (metrics['GAP'] - 4.0) * 3

        if metrics['GAN'] < -4.0:
            score -= abs(metrics['GAN'] + 4.0) * 3

        return max(0, min(100, score))


class TripReplay:
    """Manages replay of a single trip"""

    def __init__(self, codvia, route, resume_from_index=None):
        self.codvia = codvia
        self.points = route['points']
        self.original_metrics = route['metrics']

        # Resume from specific index (based on points already saved in DB)
        if resume_from_index is not None:
            self.current_index = resume_from_index
            print(f"[TripReplay] Resuming CODVIA={codvia} from index {resume_from_index}/{len(self.points)}")
        else:
            self.current_index = 0
            print(f"[TripReplay] Starting CODVIA={codvia} from beginning, total points: {len(self.points)}")

    def has_next_point(self):
        """Check if there are more points to emit"""
        return self.current_index < len(self.points)

    def get_next_point(self):
        """Get next point and advance index"""
        if not self.has_next_point():
            return None

        point = self.points[self.current_index]
        self.current_index += 1
        return point

    def get_wait_time(self, next_point):
        """Calculate wait time until next point (respecting SPEED_MULTIPLIER)"""
        if self.current_index <= 0 or self.current_index >= len(self.points):
            return 1.0  # Default 1 second

        current = self.points[self.current_index - 1]
        prev_time = datetime.fromisoformat(current['timestamp'])
        next_time = datetime.fromisoformat(next_point['timestamp'])

        delta_seconds = (next_time - prev_time).total_seconds()
        return max(0.1, delta_seconds / SPEED_MULTIPLIER)  # Minimum 0.1s

class DirijabemReplayManager:
    """Manages multiple concurrent trip replays"""

    def __init__(self):
        self.active_trips = {}  # {codusu: TripReplay instance}
        self.trips_lock = Lock()
        self.routes = self._load_routes()
        self.db_pool = None
        self.running = False

        # Synthetic data generation
        self.synthetic_generator = SyntheticRouteGenerator()
        self.metrics_calculator = BehavioralMetricsCalculator()

    def _load_routes(self):
        """Load routes from JSON file"""
        routes_path = Path(ROUTES_FILE)
        if not routes_path.exists():
            raise FileNotFoundError(f"Routes file not found: {ROUTES_FILE}")

        with open(routes_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_db_connection(self):
        """Get database connection from pool"""
        if self.db_pool is None:
            self.db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
        return self.db_pool.get_connection()

    def _check_in_progress_trip(self, codusu):
        """Check if user has trip in progress (DATAHORFIN = '1900-01-01')
        Returns (CODVIA, points_count) or None"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT v.CODVIA, COUNT(l.LOCDADCOD) as points_count
            FROM viagem v
            LEFT JOIN localizacaodados l ON l.CODVIA = v.CODVIA
            WHERE v.CODUSU = %s AND v.DATAHORFIN = '1900-01-01 00:00:00'
            GROUP BY v.CODVIA
            ORDER BY v.DATAHORINI DESC
            LIMIT 1
        """, (codusu,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result

    def _create_new_trip(self, codusu, original_codvia):
        """Create new viagem record, returns new CODVIA"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO viagem (CODUSU, DATAHORINI, DATAHORFIN, PLACA)
            VALUES (%s, NOW(), '1900-01-01 00:00:00', 'REPLAY')
        """, (codusu,))

        new_codvia = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[DIRIJABEM] Created new trip CODVIA={new_codvia} for user {codusu} (original: {original_codvia})")
        return new_codvia

    def _save_point(self, codvia, point):
        """Save GPS point to localizacaodados"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO localizacaodados (CODVIA, DATAHORA, coords, VELATU)
                VALUES (%s, NOW(), ST_PointFromText('POINT(%s %s)'), %s)
            """, (codvia, point['lon'], point['lat'], point['speed']))

            conn.commit()
        except Exception as e:
            print(f"[DIRIJABEM] Error saving point: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def _finalize_trip(self, codvia, metrics):
        """Copy metrics from original trip and set DATAHORFIN"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE viagem SET
                    DATAHORFIN = NOW(),
                    OST = %s, OSA = %s, GAA = %s, OSP = %s,
                    SAM = %s, SAA = %s,
                    BRP = %s, BRM = %s, BRA = %s,
                    GAP = %s, GAN = %s, GAM = %s,
                    SCORE = %s
                WHERE CODVIA = %s
            """, (
                metrics['OST'], metrics['OSA'], metrics['GAA'], metrics['OSP'],
                metrics['SAM'], metrics['SAA'],
                metrics['BRP'], metrics['BRM'], metrics['BRA'],
                metrics['GAP'], metrics['GAN'], metrics['GAM'],
                metrics['SCORE'],
                codvia
            ))

            conn.commit()
            print(f"[DIRIJABEM] Trip CODVIA={codvia} completed, metrics copied (SCORE={metrics['SCORE']})")
        except Exception as e:
            print(f"[DIRIJABEM] Error finalizing trip: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def start_user_trip(self, codusu):
        """Start or resume trip for user (idempotent - can call multiple times)"""
        if str(codusu) not in self.routes:
            print(f"[DIRIJABEM] User {codusu} not found in routes")
            return False

        user_data = self.routes[str(codusu)]
        username = user_data['username']

        with self.trips_lock:
            # IDEMPOTENT: If trip already active in memory, do nothing
            if codusu in self.active_trips:
                print(f"[DIRIJABEM] ✅ Trip already active for {username}, continuing...")
                return True

            # Check for in-progress trip in database
            in_progress = self._check_in_progress_trip(codusu)

            if in_progress:
                codvia, points_count = in_progress
                print(f"[DIRIJABEM] 🔄 Resuming trip for {username} (CODVIA={codvia}) from point {points_count}")

                # Find original route by CODVIA
                original_route = None
                for route in user_data['routes']:
                    if route['codvia'] == codvia:
                        original_route = route
                        break

                if not original_route:
                    print(f"[DIRIJABEM] Warning: Original route not found, choosing random")
                    original_route = random.choice(user_data['routes'])

                # Resume from point index (not timestamp)
                self.active_trips[codusu] = TripReplay(codvia, original_route, resume_from_index=points_count)
            else:
                # Start new random trip
                route = random.choice(user_data['routes'])
                original_codvia = route['codvia']
                new_codvia = self._create_new_trip(codusu, original_codvia)

                print(f"[DIRIJABEM] 🆕 Starting new trip for {username} (route {original_codvia} → CODVIA={new_codvia})")
                self.active_trips[codusu] = TripReplay(new_codvia, route)

        return True

    def start_synthetic_trip(self, codusu, driver_profile=None):
        """
        Inicia uma viagem sintética para um usuário

        Args:
            codusu: ID do usuário
            driver_profile: 'excellent', 'good', 'average', 'poor', 'aggressive'
                           Se None, escolhe aleatório com distribuição realista

        Returns:
            (codvia, driver_profile): ID da viagem criada e perfil usado
        """

        # Escolher perfil de motorista
        if driver_profile is None:
            driver_profile = DriverProfile.get_random_profile()
        elif driver_profile not in DriverProfile.PROFILES:
            print(f"[SYNTHETIC] Perfil inválido: {driver_profile}, usando 'average'")
            driver_profile = 'average'

        profile_data = DriverProfile.PROFILES[driver_profile]

        # Gerar rota sintética com perfil
        duration = random.randint(5, 20)  # 5-20 minutos
        route_points = self.synthetic_generator.generate_route(
            duration_minutes=duration,
            driver_profile=driver_profile
        )

        # Injetar eventos comportamentais contextualizados
        route_points = self.synthetic_generator.inject_realistic_events(
            route_points,
            driver_profile=driver_profile
        )

        # Calcular métricas
        metrics = self.metrics_calculator.calculate_metrics(route_points)

        # Criar registro de viagem no banco
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO viagem (CODUSU, DATAHORINI, DATAHORFIN, PLACA)
                VALUES (%s, NOW(), '1900-01-01 00:00:00', 'SYNTHETIC')
            """, (codusu,))

            codvia = cursor.lastrowid
            conn.commit()

            print(f"[SYNTHETIC] Viagem CODVIA={codvia} | Perfil: {profile_data['name']} | "
                  f"Duração: {duration}min | Pontos: {len(route_points)} | Score estimado: {metrics['SCORE']:.1f}")

        except Exception as e:
            print(f"[SYNTHETIC] Erro ao criar viagem: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return None, None
        finally:
            cursor.close()
            conn.close()

        # Criar TripReplay
        trip = TripReplay(
            codvia=codvia,
            route={'points': route_points, 'metrics': metrics, 'profile': driver_profile},
            resume_from_index=0
        )

        with self.trips_lock:
            self.active_trips[codusu] = trip

        return codvia, driver_profile

    def stop_user_trip(self, codusu):
        """Stop active trip for user"""
        with self.trips_lock:
            if codusu in self.active_trips:
                del self.active_trips[codusu]
                print(f"[DIRIJABEM] Stopped trip for user {codusu}")
                return True
        return False

    def emit_points_loop(self):
        """Main loop that emits points for all active trips"""
        print("[DIRIJABEM] Starting replay loop")

        # Track last emission time for each user
        last_emission = {}

        while self.running:
            now = time.time()

            with self.trips_lock:
                finished_users = []

                for codusu, replay in list(self.active_trips.items()):
                    # Initialize last emission time
                    if codusu not in last_emission:
                        last_emission[codusu] = 0

                    # Check if it's time to emit next point
                    time_since_last = now - last_emission[codusu]

                    if replay.has_next_point():
                        # Get wait time for next point
                        if replay.current_index > 0:
                            current = replay.points[replay.current_index - 1]
                            next_point = replay.points[replay.current_index]
                            prev_time = datetime.fromisoformat(current['timestamp'])
                            next_time = datetime.fromisoformat(next_point['timestamp'])
                            delta_seconds = (next_time - prev_time).total_seconds()
                            wait_time = max(0.1, delta_seconds / SPEED_MULTIPLIER)
                        else:
                            wait_time = 0.1  # First point, emit immediately

                        # Only emit if enough time has passed
                        if time_since_last >= wait_time:
                            point = replay.get_next_point()
                            self._save_point(replay.codvia, point)
                            last_emission[codusu] = now
                            print(f"[DIRIJABEM] User {codusu}: Emitted point {replay.current_index}/{len(replay.points)}")
                    else:
                        # Trip finished
                        self._finalize_trip(replay.codvia, replay.original_metrics)
                        finished_users.append(codusu)
                        if codusu in last_emission:
                            del last_emission[codusu]

                # Remove finished trips
                for codusu in finished_users:
                    del self.active_trips[codusu]

            time.sleep(0.1)  # Small sleep to prevent CPU spinning

    def start(self):
        """Start the replay manager"""
        self.running = True
        replay_thread = Thread(target=self.emit_points_loop, daemon=True)
        replay_thread.start()
        print("[DIRIJABEM] Replay manager started")

    def stop(self):
        """Stop the replay manager"""
        self.running = False
        print("[DIRIJABEM] Replay manager stopped")

# Global instance
replay_manager = None

def get_replay_manager():
    """Get or create global replay manager instance"""
    global replay_manager
    if replay_manager is None:
        replay_manager = DirijabemReplayManager()
        replay_manager.start()
    return replay_manager

if __name__ == "__main__":
    print("Dirijabem Replay Simulator")
    print("Starting...")

    manager = get_replay_manager()

    print("Replay manager ready. Waiting for trip requests...")
    print(f"Speed multiplier: {SPEED_MULTIPLIER}x")
    print("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop()
