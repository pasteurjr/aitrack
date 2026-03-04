# Plano: Geração de Dados para Banco Dirijabem

## Contexto

### Situação Atual

Após exploração completa do código, foi confirmado que:

**✅ Simulador AITrack (`simulator.py`):**
- Envia dados **APENAS** para o banco `tracker`
- Gera 10 veículos simulados (SIM-1000 a SIM-1009)
- 3 protocolos: Maxtrack, Suntech, Queclink
- Tabelas: `veiculos`, `localizacao`
- Conexão: `camerascasas.no-ip.info:3307` / database `tracker`

**✅ Sistema Dirijabem EXISTENTE:**
- Já existe `dirijabem_simulator.py` - Sistema de Trip Replay funcional
- Banco: `dirijabem` @ `camerascasas.no-ip.info:3307`
- 14+ tabelas incluindo: `viagem`, `localizacaodados`, `usuario`, `veiculo`
- 100 rotas reais pré-extraídas em `config/dirijabem_routes.json`
- API REST completa com 7 endpoints (`dirijabem_api.py`)
- **Sistema já integrado e operacional!**

### Problema Identificado

O usuário deseja gerar dados para o banco `dirijabem`, mas:
- O simulador principal não gera dados para dirijabem
- O `dirijabem_simulator.py` usa apenas rotas pré-extraídas (replay)
- Não há geração de dados **novos/sintéticos** para dirijabem

---

## Opções de Implementação

### Opção A: Expandir Trip Replay Existente (Recomendado - Rápido)

**O que fazer:**
Melhorar `dirijabem_simulator.py` para gerar viagens sintéticas além das pré-extraídas.

**Vantagens:**
- ✅ Sistema já existe e funciona
- ✅ Menos código para modificar
- ✅ Mantém estrutura atual
- ✅ Rápido de implementar

**Desvantagens:**
- ⚠️ Dois simuladores separados
- ⚠️ Gerenciamento independente

**Implementação:**
1. Adicionar função `generate_synthetic_trip()` em `dirijabem_simulator.py`
2. Gerar rotas aleatórias baseadas em padrões reais
3. Calcular métricas comportamentais (OST, OSA, SAM, etc.)
4. Inserir em `viagem` e `localizacaodados`

---

### Opção B: Integrar no Simulador Principal (Unificado - Complexo)

**O que fazer:**
Modificar `simulator.py` para também gerar dados para banco dirijabem.

**Vantagens:**
- ✅ Simulador único
- ✅ Gerenciamento centralizado
- ✅ Mais fácil de manter a longo prazo

**Desvantagens:**
- ⚠️ Modifica código estável
- ⚠️ Mistura lógicas diferentes (GPS raw vs trips)
- ⚠️ Mais complexo de implementar

**Implementação:**
1. Adicionar parâmetro `--dirijabem` ao `simulator.py`
2. Criar classe `DirijabemVehicle` paralela a `Vehicle`
3. Gerar viagens completas com métricas
4. Conectar aos dois bancos simultaneamente

---

### Opção C: Novo Simulador Sintético Dedicado (Ideal - Mais Trabalho)

**O que fazer:**
Criar `dirijabem_synthetic_generator.py` - novo script dedicado.

**Vantagens:**
- ✅ Separação clara de responsabilidades
- ✅ Não afeta código existente
- ✅ Pode ser mais sofisticado
- ✅ Fácil de testar isoladamente

**Desvantagens:**
- ⚠️ Mais código para manter
- ⚠️ Terceiro simulador no sistema

**Implementação:**
1. Criar novo script `dirijabem_synthetic_generator.py`
2. Classe `SyntheticTripGenerator`
3. Algoritmos de geração realista:
   - Rotas aleatórias mas plausíveis (Belo Horizonte)
   - Eventos comportamentais (speeding, harsh brake, etc.)
   - Cálculo de métricas fuzzy (OST, SAA, BRP, etc.)
4. CLI para controlar: número de viagens, usuários, etc.

---

## Recomendação: Opção A (Expandir Existente)

**Por quê:**
- Sistema já funcional
- Modificações mínimas
- Rápido de implementar
- Mantém compatibilidade

**Tempo estimado:** 3-4 horas

---

## Implementação Detalhada (Opção A)

### Arquivos a Modificar

**Arquivo:** `aitrackdatadrivr/dirijabem_simulator.py`

### Fase 1: Gerador de Rotas Sintéticas com Perfis Realistas (2h)

#### 1.1 Adicionar Classe DriverProfile

```python
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
```

#### 1.2 Adicionar Classe SyntheticRouteGenerator (Melhorada)

```python
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
```

#### 1.3 Integrar com DirijabemReplayManager (com perfis)

```python
class DirijabemReplayManager:
    def __init__(self):
        # ... código existente ...
        self.synthetic_generator = SyntheticRouteGenerator()

    def start_synthetic_trip(self, codusu, driver_profile=None):
        """
        Inicia uma viagem sintética para um usuário

        Args:
            codusu: ID do usuário
            driver_profile: 'excellent', 'good', 'average', 'poor', 'aggressive'
                           Se None, escolhe aleatório com distribuição realista
        """

        # Escolher perfil de motorista
        if driver_profile is None:
            driver_profile = DriverProfile.get_random_profile()

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

        # Criar registro de viagem no banco
        codvia = self._create_viagem_record(codusu, route_points, profile_data)

        # Criar TripReplay
        trip = TripReplay(
            codvia=codvia,
            route={'points': route_points, 'metrics': {}, 'profile': driver_profile},
            resume_from_index=0
        )

        self.active_trips[codusu] = trip

        print(f"[SYNTHETIC] Viagem CODVIA={codvia} | Perfil: {profile_data['name']} | "
              f"Duração: {duration}min | Pontos: {len(route_points)}")

        return codvia, driver_profile
```

#### 1.4 Exemplos de Dados Gerados por Perfil

**Perfil EXCELENTE (Score: 85-100)**
```
Duração: 15 min | 900 pontos | 12.3 km

Eventos:
- 0 acelerações bruscas
- 1 frenagem moderada
- 1 curva acentuada (48°)
- 5% tempo em excesso (+5 km/h)

Linha do tempo:
00:00-01: Aceleração suave 0→35 km/h
01:00-13: Velocidade constante 50-60 km/h (dentro do limite)
13:30: Curva 48° (reduziu velocidade antes)
14:00-15: Desaceleração suave 40→0 km/h

Score: 92/100 ✅ Motorista excelente
```

**Perfil MÉDIO (Score: 55-69)**
```
Duração: 15 min | 900 pontos | 12.8 km

Eventos:
- 3 acelerações bruscas (3.8, 4.1, 3.6 m/s²)
- 3 frenagens bruscas (-3.9, -4.2, -3.7 m/s²)
- 4 curvas acentuadas (52°, 68°, 55°, 72°)
- 25% tempo em excesso (+15 km/h)

Linha do tempo:
00:00-02: Aceleração rápida 0→55 km/h
03:30: ACELERAÇÃO BRUSCA 55→72 km/h
05:45: Excesso de velocidade 75 km/h (limite 60)
08:20: FRENAGEM BRUSCA 70→35 km/h
08:22: CURVA ACENTUADA 68°
12:40: Excesso constante 72-78 km/h
14:00-15: Freadas frequentes

Score: 62/100 ⚠️ Motorista médio
```

**Perfil AGRESSIVO (Score: 20-39)**
```
Duração: 15 min | 900 pontos | 14.2 km

Eventos:
- 8 acelerações bruscas (4.2, 4.8, 5.1, 4.5, 4.9, 5.3, 4.7, 5.0 m/s²)
- 7 frenagens bruscas (-4.5, -4.9, -5.2, -4.8, -5.0, -4.7, -5.1 m/s²)
- 12 curvas acentuadas (até 88°)
- 60% tempo em excesso (+25 km/h)

Linha do tempo:
00:00-01: Aceleração agressiva 0→65 km/h
01:30-08: EXCESSO CONSTANTE 78-82 km/h
03:45: ACELERAÇÃO BRUSCA 65→85 km/h (!!!)
05:20: FRENAGEM BRUSCA 85→40 km/h
05:22: CURVA BRUSCA 88° (quase capotou!)
05:25: ACELERAÇÃO COMPENSATÓRIA 40→75 km/h
08:00-12: Direção errática, múltiplas infrações
12:30: COMBO: Excesso (80) → Freada (-5.0) → Curva (75°) → Aceleração (+4.8)
14:00-15: Freadas agressivas múltiplas

Score: 28/100 ❌ Motorista PERIGOSO
```

---

### Fase 2: Cálculo de Métricas Comportamentais (1h)

#### 2.1 Adicionar BehavioralMetricsCalculator

```python
class BehavioralMetricsCalculator:
    """Calcula métricas fuzzy logic do Dirijabem"""

    def calculate_metrics(self, points: List[dict]) -> dict:
        """
        Calcula todas as 12 métricas comportamentais

        Returns: {OST, OSA, OSP, SAM, SAA, BRP, BRM, BRA, GAM, GAA, GAP, GAN}
        """
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

    def _calculate_speeding_time(self, points):
        """OST: Proporção de tempo em excesso de velocidade"""
        SPEED_LIMIT = 60  # km/h
        speeding_points = sum(1 for p in points if p['VELATU'] > SPEED_LIMIT)
        return speeding_points / len(points)

    def _calculate_speeding_avg(self, points):
        """OSA: Média de excesso de velocidade"""
        SPEED_LIMIT = 60
        excesses = [p['VELATU'] - SPEED_LIMIT for p in points if p['VELATU'] > SPEED_LIMIT]
        return sum(excesses) / len(excesses) if excesses else 0

    def _calculate_fuzzy_score(self, metrics):
        """
        Calcula score 0-100 usando lógica fuzzy simplificada
        Quanto menor o score, pior o motorista
        """
        score = 100.0

        # Penalidades
        score -= metrics['OST'] * 20  # Over-speeding time
        score -= metrics['SAA'] * 5   # Harsh accelerations
        score -= metrics['BRA'] * 3   # Aggressive turns

        return max(0, min(100, score))
```

#### 2.2 Integrar no Finalize Trip

```python
def _finalize_trip(self, trip: TripReplay):
    """Finaliza viagem calculando métricas"""

    # Buscar todos os pontos da viagem
    points = self._get_trip_points(trip.codvia)

    # Calcular métricas
    calculator = BehavioralMetricsCalculator()
    metrics = calculator.calculate_metrics(points)

    # Atualizar registro de viagem
    self._update_viagem_metrics(trip.codvia, metrics)
```

### Fase 3: API para Controlar Geração (30min)

#### 3.1 Adicionar Endpoint em dirijabem_api.py

```python
@dirijabem_bp.route('/api/dirijabem/user/<int:codusu>/start-synthetic', methods=['POST'])
def start_synthetic_trip(codusu):
    """Inicia uma viagem sintética (não replay)"""

    manager = get_replay_manager()
    codvia = manager.start_synthetic_trip(codusu)

    return jsonify({
        'success': True,
        'codvia': codvia,
        'type': 'synthetic',
        'message': 'Viagem sintética iniciada'
    })
```

### Fase 4: Script CLI para Geração em Massa (30min)

**Arquivo:** `aitrackdatadrivr/generate_dirijabem_data.py`

```python
#!/usr/bin/env python3
"""
Script CLI para gerar dados sintéticos REALISTAS em massa no banco Dirijabem
"""

import argparse
import time
from dirijabem_simulator import DirijabemReplayManager, DriverProfile

def main():
    parser = argparse.ArgumentParser(
        description='Gera dados sintéticos realistas para Dirijabem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Gerar 50 viagens com perfis aleatórios
  python generate_dirijabem_data.py --users 10 --trips-per-user 5

  # Gerar apenas motoristas ruins/agressivos (para testar alertas)
  python generate_dirijabem_data.py --users 5 --trips-per-user 10 --profile poor,aggressive

  # Gerar viagens curtas e rápidas
  python generate_dirijabem_data.py --users 20 --trips 5 --duration-min 3 --duration-max 10 --fast

  # Distribuição realista (15% excellent, 20% good, 30% average, 25% poor, 10% aggressive)
  python generate_dirijabem_data.py --users 20 --trips 5 --realistic
        """
    )

    parser.add_argument('--users', type=int, default=10, help='Número de usuários')
    parser.add_argument('--trips-per-user', '--trips', type=int, default=5,
                       help='Viagens por usuário')
    parser.add_argument('--duration-min', type=int, default=5,
                       help='Duração mínima (minutos)')
    parser.add_argument('--duration-max', type=int, default=20,
                       help='Duração máxima (minutos)')
    parser.add_argument('--profile', type=str, default=None,
                       help='Perfil(s) de motorista: excellent, good, average, poor, aggressive '
                            '(separar por vírgula para múltiplos)')
    parser.add_argument('--realistic', action='store_true',
                       help='Usar distribuição realista de perfis')
    parser.add_argument('--fast', action='store_true',
                       help='Modo rápido (não aguarda conclusão em tempo real)')

    args = parser.parse_args()

    # Processar perfis
    profiles = None
    if args.profile:
        profiles = [p.strip() for p in args.profile.split(',')]
        # Validar perfis
        valid_profiles = list(DriverProfile.PROFILES.keys())
        for p in profiles:
            if p not in valid_profiles:
                print(f"❌ Perfil inválido: {p}")
                print(f"   Perfis válidos: {', '.join(valid_profiles)}")
                return

    manager = DirijabemReplayManager()

    total_trips = args.users * args.trips_per_user
    print(f"\n{'='*70}")
    print(f"🚗 GERADOR DE DADOS SINTÉTICOS DIRIJABEM")
    print(f"{'='*70}")
    print(f"Usuários: {args.users}")
    print(f"Viagens por usuário: {args.trips_per_user}")
    print(f"Total de viagens: {total_trips}")
    print(f"Duração: {args.duration_min}-{args.duration_max} minutos")
    if profiles:
        print(f"Perfis: {', '.join(profiles)}")
    elif args.realistic:
        print(f"Perfis: Distribuição realista")
    else:
        print(f"Perfis: Aleatório")
    print(f"{'='*70}\n")

    # Estatísticas
    stats = {
        'excellent': 0,
        'good': 0,
        'average': 0,
        'poor': 0,
        'aggressive': 0
    }

    # Gerar viagens
    for codusu in range(1, args.users + 1):
        print(f"\n👤 Usuário {codusu}:")

        for trip_num in range(args.trips_per_user):
            # Escolher perfil
            if profiles:
                profile = profiles[trip_num % len(profiles)]
            elif args.realistic:
                profile = DriverProfile.get_random_profile()
            else:
                import random
                profile = random.choice(list(DriverProfile.PROFILES.keys()))

            # Gerar viagem
            codvia, actual_profile = manager.start_synthetic_trip(codusu, profile)
            stats[actual_profile] += 1

            profile_emoji = {
                'excellent': '🌟',
                'good': '👍',
                'average': '😐',
                'poor': '⚠️',
                'aggressive': '🔥'
            }

            print(f"  {profile_emoji[actual_profile]} Viagem {trip_num+1}: "
                  f"CODVIA={codvia} | Perfil: {DriverProfile.PROFILES[actual_profile]['name']}")

            # Aguardar conclusão (se não for fast mode)
            if not args.fast:
                time.sleep(0.5)  # Simula processamento

    # Resumo final
    print(f"\n{'='*70}")
    print(f"✅ GERAÇÃO CONCLUÍDA")
    print(f"{'='*70}")
    print(f"Total de viagens geradas: {total_trips}")
    print(f"\nDistribuição de perfis:")
    for profile, count in stats.items():
        percentage = (count / total_trips) * 100
        profile_name = DriverProfile.PROFILES[profile]['name']
        bar = '█' * int(percentage / 2)
        print(f"  {profile_name:12} ({profile:10}): {count:3} ({percentage:5.1f}%) {bar}")

    print(f"\n💾 Dados salvos no banco 'dirijabem'")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
```

**Uso:**
```bash
# Gerar 50 viagens com distribuição realista
python aitrackdatadrivr/generate_dirijabem_data.py --users 10 --trips-per-user 5 --realistic

# Gerar apenas motoristas ruins para testar alertas
python aitrackdatadrivr/generate_dirijabem_data.py --users 5 --trips 10 --profile poor,aggressive

# Gerar 100 viagens rápidas (não espera)
python aitrackdatadrivr/generate_dirijabem_data.py --users 20 --trips 5 --fast

# Gerar viagens curtas para testes rápidos
python aitrackdatadrivr/generate_dirijabem_data.py --users 5 --trips 3 --duration-min 3 --duration-max 8 --fast
```

**Saída esperada:**
```
======================================================================
🚗 GERADOR DE DADOS SINTÉTICOS DIRIJABEM
======================================================================
Usuários: 10
Viagens por usuário: 5
Total de viagens: 50
Duração: 5-20 minutos
Perfis: Distribuição realista
======================================================================

👤 Usuário 1:
  🌟 Viagem 1: CODVIA=12345 | Perfil: Excelente
  👍 Viagem 2: CODVIA=12346 | Perfil: Bom
  😐 Viagem 3: CODVIA=12347 | Perfil: Médio
  ...

======================================================================
✅ GERAÇÃO CONCLUÍDA
======================================================================
Total de viagens geradas: 50

Distribuição de perfis:
  Excelente    (excellent ): 8 ( 16.0%) ████████
  Bom          (good      ): 10 ( 20.0%) ██████████
  Médio        (average   ): 15 ( 30.0%) ███████████████
  Ruim         (poor      ): 12 ( 24.0%) ████████████
  Agressivo    (aggressive): 5 ( 10.0%) █████

💾 Dados salvos no banco 'dirijabem'
======================================================================
```

---

## Estrutura de Dados Gerados

### Tabela `viagem`

```sql
INSERT INTO viagem (
  CODUSU, PLACA, DATAHORINI, DATAHORFIN, DISTANCIA, DURACAO,
  OST, OSA, OSP, SAM, SAA, BRP, BRM, BRA, GAM, GAA, GAP, GAN, SCORE
) VALUES (
  1, 'ABC1234', '2026-03-02 18:00:00', '2026-03-02 18:15:00', 8.5, 15.0,
  0.23, 12.5, 18.3, 3, 1, 85.2, 5, 2, 0.35, 0.12, 4.2, -5.8, 73.5
);
```

### Tabela `localizacaodados`

```sql
INSERT INTO localizacaodados (
  CODVIA, DATAHORA, coords, VELATU, ACELLINATU, VARDIRATU
) VALUES (
  12345, '2026-03-02 18:00:01', ST_PointFromText('POINT(-43.920 -19.950)'), 35.2, 1.2, 5.3
);
-- Mais ~900 pontos (15 minutos × 60 pontos/minuto)
```

---

## Verificação

### Testes Manuais

```bash
# 1. Iniciar sistema
python run.py

# 2. Gerar viagem sintética via API
curl -X POST http://localhost:5009/api/dirijabem/user/1/start-synthetic

# 3. Verificar no banco
mysql -h camerascasas.no-ip.info -P 3307 -u producao -p112358123 dirijabem \
  -e "SELECT CODVIA, CODUSU, DISTANCIA, DURACAO, SCORE FROM viagem ORDER BY CODVIA DESC LIMIT 5;"

# 4. Verificar pontos GPS
mysql ... -e "SELECT COUNT(*) FROM localizacaodados WHERE CODVIA = 12345;"

# 5. Gerar em massa
python aitrackdatadrivr/generate_dirijabem_data.py --users 5 --trips-per-user 3
```

### Validações

- ✅ Viagens aparecem em `viagem` com métricas calculadas
- ✅ Pontos GPS em `localizacaodados` (~900 por viagem de 15 min)
- ✅ Coordenadas dentro de Belo Horizonte
- ✅ Velocidades realistas (0-80 km/h)
- ✅ Métricas comportamentais calculadas (OST, SAA, BRP, etc.)
- ✅ Score entre 0-100
- ✅ API retorna viagens sintéticas no frontend

---

## Arquivos a Criar/Modificar

**Novos:**
- `aitrackdatadrivr/generate_dirijabem_data.py` - Script CLI

**Modificados:**
- `aitrackdatadrivr/dirijabem_simulator.py` - Adicionar geração sintética
- `aitrackdatadrivr/server/dirijabem_api.py` - Endpoint /start-synthetic

---

## Estimativa de Tempo

- Fase 1: Gerador sintético com perfis - 2h (melhorado!)
- Fase 2: Cálculo de métricas - 1h
- Fase 3: API endpoint - 30min
- Fase 4: Script CLI melhorado - 45min (mais features)
- Testes e ajustes - 45min

**Total: 5 horas** (1h a mais que versão básica, mas MUITO mais útil!)

---

## Benefícios da Solução Melhorada

### ✅ Realismo e Utilidade para Testes

**Solução Básica (4h):**
- Eventos aleatórios sem contexto
- Não tem perfis de motorista
- Falta frenagens bruscas
- Dados pouco realistas
- ⚠️ Limitado para testar aplicação

**Solução Melhorada (5h):**
- ✅ 5 perfis comportamentais realistas
- ✅ Eventos contextualizados (freada antes da curva, etc.)
- ✅ Frenagens bruscas incluídas
- ✅ Combos situacionais (excesso→freada→curva)
- ✅ Distribuição natural (70% normal, 30% eventos)
- ✅ **MUITO útil para testar aplicação!**

### 🎯 Casos de Uso para Teste

**1. Testar Sistema de Alertas**
```bash
# Gerar motoristas ruins/agressivos para disparar alertas
python generate_dirijabem_data.py --users 10 --trips 5 --profile poor,aggressive
```
→ Resultados: 50 viagens com múltiplos eventos, scores baixos (20-54), ideal para testar detecção de alertas

**2. Testar Dashboard de Scores**
```bash
# Gerar distribuição realista para visualizar gráficos
python generate_dirijabem_data.py --users 20 --trips 5 --realistic
```
→ Resultados: 100 viagens com scores variados (20-100), perfeito para testar dashboard

**3. Testar Replay de Viagens**
```bash
# Gerar viagens curtas para replay rápido
python generate_dirijabem_data.py --users 5 --trips 10 --duration-min 3 --duration-max 8 --fast
```
→ Resultados: 50 viagens de 3-8 minutos, ideal para testar player de replay

**4. Testar Performance com Volume**
```bash
# Gerar muitas viagens rapidamente
python generate_dirijabem_data.py --users 50 --trips 20 --fast
```
→ Resultados: 1000 viagens (~900k pontos GPS), testa performance do banco e API

### 📊 Qualidade dos Dados Gerados

| Métrica | Solução Básica | Solução Melhorada |
|---------|---------------|-------------------|
| **Perfis de motorista** | ❌ Não tem | ✅ 5 perfis realistas |
| **Frenagens bruscas** | ❌ Não tem | ✅ 0-10 por viagem |
| **Contexto de eventos** | ❌ Aleatório | ✅ Contextualizado |
| **Distribuição realista** | ❌ Uniforme | ✅ Natural (70/30) |
| **Combos situacionais** | ❌ Não tem | ✅ Sim |
| **Útil para testar?** | ⚠️ Limitado | ✅ **Excelente** |
| **Tempo implementação** | 4h | 5h (+1h) |
| **Valor agregado** | Baixo | **MUITO ALTO** |

### 🚀 Outros Benefícios

✅ **Geração ilimitada** - Crie quantas viagens quiser
✅ **Controle total** - Escolha perfis específicos ou distribuição realista
✅ **Não depende de dados reais** - Funciona offline
✅ **Útil para Monitor AI** - Dados realistas para treinar/testar IA
✅ **Compatibilidade** - Mantém replay de rotas reais existente
✅ **CLI poderoso** - Múltiplas opções para diferentes cenários de teste
✅ **Visualização clara** - Frontend pode mostrar eventos realistas

### 💎 Conclusão

**Vale a pena 1 hora extra de implementação?**

**SIM!** A diferença de qualidade é ENORME:
- Dados básicos: "Funcionam, mas pouco úteis"
- Dados melhorados: "Perfeitos para testar a aplicação de forma realista"

Com a solução melhorada, você pode:
- Testar todos os tipos de motorista (excelente até agressivo)
- Visualizar eventos realistas no mapa
- Validar sistema de alertas com dados que fazem sentido
- Demonstrar a aplicação com dados convincentes
