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

### Fase 1: Gerador de Rotas Sintéticas (1.5h)

#### 1.1 Adicionar Classe SyntheticRouteGenerator

```python
class SyntheticRouteGenerator:
    """Gera rotas sintéticas realistas para Belo Horizonte"""

    def __init__(self):
        # Bounds de Belo Horizonte
        self.LAT_MIN = -19.96
        self.LAT_MAX = -19.94
        self.LON_MIN = -43.93
        self.LON_MAX = -43.91

        # Parâmetros de realismo
        self.AVG_SPEED = 40  # km/h
        self.MAX_SPEED = 80  # km/h
        self.POINT_INTERVAL = 1  # segundos

    def generate_route(self, duration_minutes=10, distance_km=5):
        """
        Gera uma rota sintética com pontos GPS

        Returns: List[dict] com estrutura compatível com rotas reais
        """
        points = []
        num_points = duration_minutes * 60  # 1 por segundo

        # Ponto inicial aleatório
        start_lat = random.uniform(self.LAT_MIN, self.LAT_MAX)
        start_lon = random.uniform(self.LON_MIN, self.LON_MAX)

        # Gerar trajetória
        for i in range(num_points):
            # Calcular deslocamento gradual
            lat, lon = self._calculate_next_point(...)
            speed = self._realistic_speed(i, num_points)

            points.append({
                'DATAHORA': start_time + timedelta(seconds=i),
                'VELATU': speed,
                'ACELLINATU': self._calculate_accel(...),
                'VARDIRATU': self._calculate_bearing_change(...),
                'coords': (lat, lon)
            })

        return points

    def _calculate_next_point(self, current_lat, current_lon, speed, heading):
        """Calcula próximo ponto GPS baseado em velocidade e direção"""
        # Distância percorrida em 1 segundo
        distance_m = (speed / 3.6)  # km/h para m/s

        # Conversão para delta lat/lon
        delta_lat = ...
        delta_lon = ...

        return new_lat, new_lon

    def _realistic_speed(self, point_index, total_points):
        """Velocidade realista com acelerações/desacelerações"""
        # Simula aceleração no início, velocidade constante, desaceleração no fim
        if point_index < 30:  # Primeiros 30s - acelerando
            return (point_index / 30) * self.AVG_SPEED
        elif point_index > total_points - 30:  # Últimos 30s - desacelerando
            return ((total_points - point_index) / 30) * self.AVG_SPEED
        else:  # Meio da viagem - velocidade normal com variações
            return self.AVG_SPEED + random.gauss(0, 5)

    def inject_behavioral_events(self, points):
        """Injeta eventos comportamentais aleatórios"""
        # Harsh acceleration
        for i in [random.randint(0, len(points)-1) for _ in range(2)]:
            points[i]['ACELLINATU'] = random.uniform(3.0, 5.0)

        # Sharp turns
        for i in [random.randint(0, len(points)-1) for _ in range(3)]:
            points[i]['VARDIRATU'] = random.uniform(45, 90)

        # Speeding
        for i in range(len(points) // 4, len(points) // 2):
            points[i]['VELATU'] = min(points[i]['VELATU'] * 1.3, self.MAX_SPEED)

        return points
```

#### 1.2 Integrar com DirijabemReplayManager

```python
class DirijabemReplayManager:
    def __init__(self):
        # ... código existente ...
        self.synthetic_generator = SyntheticRouteGenerator()

    def start_synthetic_trip(self, codusu):
        """Inicia uma viagem sintética para um usuário"""

        # Gerar rota sintética
        duration = random.randint(5, 20)  # 5-20 minutos
        distance = duration * 0.5  # ~30 km/h médio

        route_points = self.synthetic_generator.generate_route(
            duration_minutes=duration,
            distance_km=distance
        )

        # Injetar eventos comportamentais
        route_points = self.synthetic_generator.inject_behavioral_events(route_points)

        # Criar registro de viagem
        codvia = self._create_viagem_record(codusu, route_points)

        # Criar TripReplay
        trip = TripReplay(
            codvia=codvia,
            route={'points': route_points, 'metrics': {}},
            resume_from_index=0
        )

        self.active_trips[codusu] = trip
        return codvia
```

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
Script CLI para gerar dados sintéticos em massa no banco Dirijabem
"""

import argparse
from dirijabem_simulator import DirijabemReplayManager

def main():
    parser = argparse.ArgumentParser(description='Gera dados sintéticos para Dirijabem')
    parser.add_argument('--users', type=int, default=10, help='Número de usuários')
    parser.add_argument('--trips-per-user', type=int, default=5, help='Viagens por usuário')
    parser.add_argument('--duration-min', type=int, default=5, help='Duração mínima (min)')
    parser.add_argument('--duration-max', type=int, default=20, help='Duração máxima (min)')

    args = parser.parse_args()

    manager = DirijabemReplayManager()

    print(f"Gerando {args.users * args.trips_per_user} viagens sintéticas...")

    for codusu in range(1, args.users + 1):
        print(f"\nUsuário {codusu}:")

        for trip_num in range(args.trips_per_user):
            codvia = manager.start_synthetic_trip(codusu)

            # Aguardar conclusão (ou modo rápido)
            # ...

            print(f"  ✓ Viagem {trip_num+1}: CODVIA={codvia}")

    print(f"\n✅ {args.users * args.trips_per_user} viagens geradas com sucesso!")

if __name__ == '__main__':
    main()
```

**Uso:**
```bash
# Gerar 50 viagens (10 usuários × 5 viagens cada)
python aitrackdatadrivr/generate_dirijabem_data.py --users 10 --trips-per-user 5

# Gerar 100 viagens rápidas
python aitrackdatadrivr/generate_dirijabem_data.py --users 20 --trips-per-user 5 --duration-min 3 --duration-max 10
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

- Fase 1: Gerador sintético - 1.5h
- Fase 2: Cálculo de métricas - 1h
- Fase 3: API endpoint - 30min
- Fase 4: Script CLI - 30min
- Testes e ajustes - 30min

**Total: 4 horas**

---

## Benefícios

✅ Geração ilimitada de dados de teste
✅ Controle sobre padrões comportamentais
✅ Não depende de dados reais
✅ Útil para testes do Monitor AI
✅ Mantém compatibilidade com replay existente
