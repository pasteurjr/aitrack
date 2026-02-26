# Especificação: Integração DataDrivr + AITrack

## 1. Executive Summary

### Visão Geral
Este documento especifica a integração entre o **DataDrivr** (sistema de monitoramento comportamental de motoristas) e o **AITrack** (sistema de rastreamento veicular em tempo real). A integração adiciona capacidades de análise comportamental, detecção de eventos de risco e gamificação ao rastreamento de frotas.

### Benefícios da Integração

**Para Gestores de Frota:**
- Identificação de motoristas de risco em tempo real
- Redução de sinistros através de coaching comportamental
- Economia em combustível e manutenção (até 15%)
- Evidências objetivas para treinamentos

**Para Seguradoras:**
- Precificação baseada em risco real (telemática)
- Detecção de fraudes (correlação de eventos com sinistros)
- Redução de sinistralidade (20-30%)
- Validação automática de sinistros

**Para Motoristas:**
- Feedback imediato sobre comportamento
- Gamificação com recompensas
- Redução de custos operacionais
- Conscientização sobre direção segura

### Proposta de Valor

```
AITrack Atual                      AITrack + DataDrivr
┌─────────────────┐               ┌─────────────────────────┐
│ GPS Tracking    │               │ GPS + Behavioral AI     │
│ Speed           │    +          │ 8 Behavioral Metrics    │
│ Route History   │  ====>        │ Event Detection         │
│ Basic Alerts    │               │ Risk Scoring            │
└─────────────────┘               │ Predictive Insights     │
                                  │ Gamification            │
                                  │ Insurance Integration   │
                                  └─────────────────────────┘
```

**ROI Esperado:**
- Redução de 25% em eventos de risco nos primeiros 3 meses
- Economia de 10-15% em combustível
- Redução de 20% em custos de manutenção
- Diminuição de 30% em prêmios de seguro (com parceiros)

---

## 2. DataDrivr Architecture Analysis

### 2.1 DataDrivr Mobile App

**Tecnologia:** React Native + Expo (iOS, Android, Web)

**Dados Coletados:**
| Sensor | Métrica | Frequência | Uso |
|--------|---------|-----------|-----|
| GPS | Lat/Lon/Alt | 1 Hz | Posição, velocidade calculada |
| Accelerometer | 3-axis (m/s²) | 10 Hz | Aceleração/frenagem brusca |
| Gyroscope | Rotação angular | 10 Hz | Curvas acentuadas |
| Compass | Heading (0-360°) | 1 Hz | Mudanças de direção |
| Device | Timestamp | Contínuo | Sincronização de eventos |

**Sistema de Scoring Comportamental (8 Métricas):**

1. **Controle de Velocidade (25% do score)**
   - Violações de limite
   - Tempo acima do limite
   - Velocidade excessiva em zonas urbanas

2. **Suavidade de Aceleração (20%)**
   - Acelerações bruscas (> 2 m/s²)
   - Frequência de eventos
   - Intensidade média

3. **Qualidade de Frenagem (20%)**
   - Frenagens bruscas (> 3 m/s²)
   - Antecipação (distância para obstáculos)
   - Padrão de desaceleração

4. **Curvas e Manobras (15%)**
   - Velocidade em curvas
   - Ângulo de rotação
   - Estabilidade lateral

5. **Detecção de Distração (10%)**
   - Uso de celular durante direção
   - Padrões erráticos de velocidade

6. **Fator Hora do Dia (5%)**
   - Direção noturna (22h-6h)
   - Condições climáticas
   - Visibilidade

7. **Detecção de Fadiga (3%)**
   - Duração da viagem
   - Consistência do comportamento
   - Micro-correções de direção

8. **Locais Perigosos (2%)**
   - Histórico de acidentes no local
   - Densidade de tráfego
   - Condições da via

**Fórmula de Score Geral:**
```
Score = (0.25 × Velocidade) + (0.20 × Aceleração) + (0.20 × Frenagem) +
        (0.15 × Curvas) + (0.10 × Distração) + (0.05 × HoraDia) +
        (0.03 × Fadiga) + (0.02 × Locais)
```

**Sistema de Alertas em Tempo Real:**
- Velocidade acima do limite + 10 km/h
- Aceleração brusca detectada
- Frenagem de emergência
- Consumo anômalo de combustível

**Gamificação:**
- Pontos por viagens seguras (100-1000 pts)
- Desafios semanais/mensais
- Conquistas com raridade (Comum → Lendária)
- Ranking entre motoristas
- Recompensas: Vouchers, descontos, serviços

### 2.2 DataDrivr Insurance-Web

**Tecnologia:** React + TypeScript + Redux Toolkit + Material-UI

**7 Módulos Analíticos:**

**A. Análise Comportamental**
- Score evolutivo (linha temporal)
- Distribuição de scores (pie chart)
- Top/bottom performers
- Padrões de direção identificados
- Recomendações personalizadas

**B. Avaliação de Risco**
- Score de risco preditivo (0-1000)
- Distribuição por categoria
- Fatores de risco primários
- Clientes de alto risco
- Tendências (up/down/stable)

**C. Detecção de Fraude**
- Casos suspeitos
- Taxa de detecção
- Indicadores (sinistros múltiplos, mudança comportamental, locais isolados)
- Economia gerada
- Status de investigação

**D. Processamento de Sinistros**
- Funil de processamento (recebido → triagem → análise → aprovação → pagamento)
- Tempo médio vs SLA
- Taxa de automação
- Satisfação do cliente
- Distribuição por tipo (colisão, roubo, incêndio)

**E. Otimização de Precificação**
- Prêmio médio por segmento
- Margem de lucro
- Taxa de conversão
- Oportunidades de otimização
- Elasticidade de preço

**F. Análise Temporal**
- Timeline de eventos (100+ minutos de viagem)
- Scatter plot: Exposição vs Risco
- Evolução de vetores de risco (comportamental, contextual, hábitos, exposição)
- Detecção de sensibilidade

**G. Coach Personalizado**
- Score atual vs meta
- Programas ativos (Eco-driver, Defensive, Speed Control)
- Conquistas desbloqueadas
- Recomendações priorizadas
- Economia mensal estimada

**Visualizações-Chave:**
- Line charts (tendências)
- Pie/Donut charts (distribuições)
- Radar charts (análise multidimensional)
- Scatter plots (correlações)
- Funnel charts (processos)
- Timeline com marcadores de eventos

---

## 3. AITrack Current State

### 3.1 Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────┐
│                     AITrack Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Trackers (Maxtrack/Suntech/Queclink)                      │
│       │                                                      │
│       ▼ TCP Port 9000                                       │
│  ┌──────────────────┐                                       │
│  │ Socket Server    │  Receives raw GPS packets            │
│  │ (Python)         │  ThreadPoolExecutor (20 workers)     │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────┐                                       │
│  │ Protocol Parsers │  Maxtrack, Suntech, Queclink        │
│  │ (Python)         │  Returns standardized JSON           │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────┐                                       │
│  │ DB Handler       │  MySQL Connection Pool (15 conns)    │
│  │ (Python)         │  Saves to veiculos + localizacao     │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────┐          │
│  │ MySQL Database (tracker)                     │          │
│  │ - veiculos (VEICOD, VEIPLACA, VEI_DEVICE_ID)│          │
│  │ - localizacao (FK_VEICOD, LOCLATLONG POINT, │          │
│  │               DATAHORA, VELATU, ALTITUDE)    │          │
│  └──────────────────┬───────────────────────────┘          │
│                     │                                       │
│                     ▼ HTTP Port 5000                        │
│  ┌──────────────────────────────────────┐                  │
│  │ REST API (Flask)                     │                  │
│  │ - GET /api/positions (all vehicles)  │                  │
│  │ - CORS enabled                       │                  │
│  └──────────────────┬───────────────────┘                  │
│                     │                                       │
│                     ▼ HTTP                                  │
│  ┌──────────────────────────────────────┐                  │
│  │ Frontend (React + TypeScript)        │                  │
│  │ - Leaflet map                        │                  │
│  │ - Vehicle list sidebar               │                  │
│  │ - Basic markers with popup           │                  │
│  │ - Auto-center on selected vehicle    │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Capacidades Atuais

**Dados Rastreados:**
- Posição GPS (lat/lon)
- Velocidade instantânea
- Orientação (heading)
- Status de ignição
- Voltagem da bateria
- Altitude

**Protocolos Suportados:**
- Maxtrack (sem device_id, usa IP:port)
- Suntech (com device_id)
- Queclink (com device_id + altitude)

**Funcionalidades Frontend:**
- Mapa com marcadores de veículos
- Lista de veículos na sidebar
- Popup com informações básicas
- Centralização automática no veículo selecionado
- Atualização a cada 5 segundos (polling)

**Simulador:**
- 10 veículos simulados
- Rotas reais de São Paulo (config/routes.json)
- Alternância entre protocolos Suntech/Queclink
- Envio a cada 5 segundos
- Velocidade aleatória (20-60 km/h)

### 3.3 Limitações Identificadas

**Sem Análise Comportamental:**
- Não detecta eventos de risco (frenagens, acelerações bruscas)
- Não calcula scores de direção
- Não identifica padrões perigosos

**Visualização Básica:**
- Marcadores uniformes (sem diferenciação de risco)
- Sem alertas em tempo real
- Sem histórico de eventos no mapa
- Sem dashboard analítico

**Sem Inteligência:**
- Não aprende padrões
- Não prevê riscos
- Não oferece insights
- Não sugere melhorias

**Sem Gamificação:**
- Não engaja motoristas
- Sem recompensas
- Sem ranking

---

## 4. Integration Strategy

### 4.1 Data Layer Integration

#### Nova Estrutura de Banco de Dados

**Tabela: `vehicle_events`**
```sql
CREATE TABLE vehicle_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(50) NOT NULL,
  vehicle_id INT,
  event_type ENUM('harsh_accel', 'harsh_brake', 'speeding', 'sharp_turn', 'phone_usage', 'fatigue') NOT NULL,
  severity ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  timestamp DATETIME NOT NULL,
  latitude DOUBLE NOT NULL,
  longitude DOUBLE NOT NULL,
  speed FLOAT,
  heading FLOAT,
  acceleration FLOAT,
  score_impact INT,
  metadata JSON,
  INDEX idx_device_timestamp (device_id, timestamp),
  INDEX idx_event_type (event_type),
  INDEX idx_severity (severity),
  FOREIGN KEY (vehicle_id) REFERENCES veiculos(VEICOD)
) ENGINE=InnoDB;
```

**Tabela: `vehicle_scores`**
```sql
CREATE TABLE vehicle_scores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(50) NOT NULL,
  vehicle_id INT,
  score_overall FLOAT NOT NULL,
  score_speed FLOAT,
  score_acceleration FLOAT,
  score_braking FLOAT,
  score_cornering FLOAT,
  score_distraction FLOAT,
  score_time_of_day FLOAT,
  score_fatigue FLOAT,
  score_hazardous_locations FLOAT,
  trip_count INT DEFAULT 0,
  total_distance FLOAT DEFAULT 0,
  total_duration INT DEFAULT 0,
  last_updated DATETIME NOT NULL,
  INDEX idx_device (device_id),
  INDEX idx_score (score_overall),
  FOREIGN KEY (vehicle_id) REFERENCES veiculos(VEICOD)
) ENGINE=InnoDB;
```

**Tabela: `trips`**
```sql
CREATE TABLE trips (
  id INT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(50) NOT NULL,
  vehicle_id INT,
  start_time DATETIME NOT NULL,
  end_time DATETIME,
  start_lat DOUBLE,
  start_lon DOUBLE,
  end_lat DOUBLE,
  end_lon DOUBLE,
  distance FLOAT,
  duration INT,
  avg_speed FLOAT,
  max_speed FLOAT,
  score FLOAT,
  events_count INT DEFAULT 0,
  fuel_consumption FLOAT,
  status ENUM('active', 'completed', 'interrupted') DEFAULT 'active',
  INDEX idx_device_time (device_id, start_time),
  INDEX idx_status (status),
  FOREIGN KEY (vehicle_id) REFERENCES veiculos(VEICOD)
) ENGINE=InnoDB;
```

**Tabela: `gamification`**
```sql
CREATE TABLE gamification (
  id INT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(50) NOT NULL,
  points INT DEFAULT 0,
  level INT DEFAULT 1,
  achievements JSON,
  challenges JSON,
  rank_position INT,
  last_updated DATETIME NOT NULL,
  UNIQUE KEY idx_device (device_id)
) ENGINE=InnoDB;
```

#### Motor de Cálculo de Scores

**Arquivo: `server/behavioral_engine.py`**

```python
class BehavioralEngine:
    def __init__(self):
        self.speed_threshold_urban = 60  # km/h
        self.speed_threshold_highway = 120  # km/h
        self.harsh_accel_threshold = 2.0  # m/s²
        self.harsh_brake_threshold = 3.0  # m/s²
        self.sharp_turn_threshold = 45  # degrees

    def detect_events(self, current_data, previous_data):
        """Detecta eventos comportamentais"""
        events = []

        # 1. Detecção de Aceleração Brusca
        if previous_data:
            speed_delta = current_data['speed'] - previous_data['speed']
            time_delta = (current_data['timestamp'] - previous_data['timestamp']).seconds
            if time_delta > 0:
                acceleration = (speed_delta / 3.6) / time_delta  # m/s²
                if acceleration > self.harsh_accel_threshold:
                    events.append({
                        'type': 'harsh_accel',
                        'severity': self._calculate_severity(acceleration, self.harsh_accel_threshold),
                        'value': acceleration
                    })

        # 2. Detecção de Frenagem Brusca
        # Similar logic for braking

        # 3. Detecção de Excesso de Velocidade
        if current_data['speed'] > self.speed_threshold_urban + 10:
            events.append({
                'type': 'speeding',
                'severity': self._calculate_speeding_severity(current_data['speed']),
                'value': current_data['speed']
            })

        # 4. Detecção de Curvas Acentuadas
        # Check heading change

        return events

    def calculate_score(self, device_id, timeframe='24h'):
        """Calcula score comportamental"""
        # Query events from DB
        # Apply scoring algorithm
        # Return 8-metric breakdown
        pass
```

### 4.2 Behavioral Scoring System

#### Adaptação para Rastreamento de Frotas

**Diferenças: Insurance vs Fleet:**

| Aspecto | Insurance (DataDrivr) | Fleet (AITrack) |
|---------|----------------------|-----------------|
| Foco | Cálculo de prêmio | Gestão de risco operacional |
| Métricas | 8 dimensões | 3-5 dimensões prioritárias |
| Frequência | Batch (fim de viagem) | Real-time (contínuo) |
| Granularidade | Individual detalhado | Agregado por veículo/motorista |
| Ação | Ajuste de apólice | Alerta + coaching imediato |

**Métricas Priorizadas para Fleet:**
1. **Velocidade** (30%) - Impacto direto em acidentes e combustível
2. **Frenagem** (35%) - Indicador de antecipação e segurança
3. **Aceleração** (35%) - Economia de combustível e desgaste

**Algoritmo Simplificado (v1.0):**
```python
def calculate_fleet_score(events, trip_data):
    # Base score
    score = 100

    # Penalizações
    harsh_brake_penalty = events['harsh_brake']['count'] * 5
    harsh_accel_penalty = events['harsh_accel']['count'] * 4
    speeding_penalty = events['speeding']['duration_minutes'] * 2

    final_score = max(0, score - harsh_brake_penalty - harsh_accel_penalty - speeding_penalty)

    return {
        'overall': final_score,
        'speed': 100 - speeding_penalty,
        'braking': 100 - harsh_brake_penalty,
        'acceleration': 100 - harsh_accel_penalty
    }
```

### 4.3 Event Detection Engine

#### Algoritmos de Detecção

**1. Aceleração Brusca**
```python
# Delta de velocidade em 3 segundos
if (speed_now - speed_3s_ago) / 3.6 / 3 > 2.0:  # > 2 m/s²
    trigger_event('harsh_accel', severity='medium')
```

**2. Frenagem Brusca**
```python
# Desaceleração rápida
if (speed_3s_ago - speed_now) / 3.6 / 3 > 3.0:  # > 3 m/s²
    trigger_event('harsh_brake', severity='high')
```

**3. Excesso de Velocidade**
```python
# Configurable per route/zone
if speed > speed_limit + 10:
    duration = time_above_limit
    trigger_event('speeding', severity=duration_to_severity(duration))
```

**4. Curvas Acentuadas**
```python
# Mudança de heading em velocidade
heading_change = abs(heading_now - heading_5s_ago)
if heading_change > 45 and speed > 30:
    trigger_event('sharp_turn', severity='medium')
```

#### Pipeline de Processamento

```
GPS Data → Event Detection → Severity Classification → Score Impact → Alert Generation
   │              │                    │                      │               │
   │              │                    │                      │               ▼
   │              │                    │                      │         ┌──────────┐
   │              │                    │                      │         │ Frontend │
   │              │                    │                      │         │  Alert   │
   │              │                    │                      │         └──────────┘
   │              │                    │                      ▼
   │              │                    │              ┌───────────────┐
   │              │                    │              │ Score Update  │
   │              │                    │              │  (Running Avg)│
   │              │                    │              └───────────────┘
   │              │                    ▼
   │              │            ┌──────────────┐
   │              │            │ DB: Insert   │
   │              │            │ vehicle_     │
   │              │            │ events       │
   │              │            └──────────────┘
   │              ▼
   │      ┌──────────────────┐
   │      │ Event Classifier │
   │      │ harsh_accel,     │
   │      │ harsh_brake,     │
   │      │ speeding,        │
   │      │ sharp_turn       │
   │      └──────────────────┘
   ▼
┌─────────────────┐
│ Raw Telemetry   │
│ lat, lon, speed,│
│ heading, time   │
└─────────────────┘
```

### 4.4 Frontend Enhancements

#### Marcadores de Veículos Color-Coded

```typescript
function getMarkerColor(score: number): string {
  if (score >= 75) return '#10b981'; // Green - Good
  if (score >= 50) return '#f59e0b'; // Orange - Moderate
  return '#ef4444'; // Red - Poor
}

function getMarkerIcon(vehicle: Vehicle): L.Icon {
  return L.divIcon({
    html: `
      <div style="
        background: ${getMarkerColor(vehicle.score)};
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        border: 2px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      ">
        ${vehicle.score}
      </div>
    `,
    className: 'behavioral-marker',
    iconSize: [30, 30]
  });
}
```

#### Event Markers no Mapa

```typescript
interface EventMarker {
  id: string;
  type: 'harsh_accel' | 'harsh_brake' | 'speeding' | 'sharp_turn';
  lat: number;
  lon: number;
  timestamp: Date;
  severity: 'low' | 'medium' | 'high';
}

const eventIcons = {
  harsh_accel: '⚡',
  harsh_brake: '🛑',
  speeding: '🚨',
  sharp_turn: '↪️'
};
```

#### Behavioral Dashboard Component

```typescript
interface BehavioralDashboardProps {
  vehicles: Vehicle[];
  events: Event[];
  scores: VehicleScore[];
}

const BehavioralDashboard: React.FC<BehavioralDashboardProps> = ({
  vehicles, events, scores
}) => {
  const fleetAverage = calculateFleetAverage(scores);
  const topPerformers = scores.sort((a, b) => b.overall - a.overall).slice(0, 3);
  const bottomPerformers = scores.sort((a, b) => a.overall - b.overall).slice(0, 3);

  return (
    <div className="behavioral-dashboard">
      {/* Fleet Overview */}
      <div className="overview-cards">
        <KPICard title="Fleet Score" value={fleetAverage} trend="+3.2%" />
        <KPICard title="Events Today" value={events.length} trend="-15%" />
        <KPICard title="Active Vehicles" value={vehicles.length} />
      </div>

      {/* Real-time Alerts */}
      <AlertPanel events={events.filter(e => e.active)} />

      {/* Score Distribution Chart */}
      <ScoreDistributionChart scores={scores} />

      {/* Leaderboard */}
      <Leaderboard top={topPerformers} bottom={bottomPerformers} />
    </div>
  );
};
```

---

## 5. Use Cases

### 5.1 Fleet Management

#### UC-01: Monitor Real-time Driver Safety

**Ator:** Gestor de Frota

**Fluxo:**
1. Gestor acessa dashboard AITrack
2. Visualiza mapa com veículos color-coded (verde/amarelo/vermelho)
3. Identifica veículo vermelho (score < 50)
4. Clica no marcador → vê eventos recentes (3 frenagens bruscas, 2 excessos de velocidade)
5. Aciona alerta para motorista via rádio/telefone
6. Acompanha melhoria do score em tempo real

**Valor:** Intervenção imediata reduz risco de acidente

#### UC-02: Weekly Safety Report

**Ator:** Gestor de Frota

**Fluxo:**
1. Sistema gera relatório semanal automático
2. Lista top 10 motoristas (scores > 80)
3. Lista bottom 10 motoristas (scores < 60)
4. Destaca padrões: "Motorista X tem 15 frenagens bruscas às 18h (rush hour)"
5. Sugere treinamento específico

**Valor:** Decisões baseadas em dados objetivos

### 5.2 Insurance Integration

#### UC-03: Pay-How-You-Drive (PHYD)

**Ator:** Seguradora Parceira

**Fluxo:**
1. Seguradora acessa API AITrack
2. Obtém score médio mensal por veículo
3. Aplica desconto progressivo:
   - Score 90-100: -30% no prêmio
   - Score 80-89: -20%
   - Score 70-79: -10%
   - Score < 70: prêmio normal
4. Notifica cliente sobre economia

**Valor:** Incentivo financeiro para direção segura

#### UC-04: Claims Validation

**Ator:** Analista de Sinistros

**Fluxo:**
1. Sinistro reportado: "Colisão traseira às 15:30"
2. Analista verifica dados AITrack do horário
3. Identifica: frenagem brusca registrada às 15:29
4. Velocidade antes do evento: 80 km/h em zona de 60 km/h
5. Conclusão: cliente em excesso de velocidade
6. Ajusta responsabilidade no sinistro

**Valor:** Redução de fraudes e pagamentos indevidos

### 5.3 Maintenance Prediction

#### UC-05: Predictive Maintenance

**Ator:** Gestor de Manutenção

**Fluxo:**
1. Sistema analisa padrão de direção de veículo X
2. Detecta: 50 acelerações bruscas/semana (média da frota: 10)
3. Calcula desgaste acelerado de:
   - Pastilhas de freio (substituição antecipada em 30%)
   - Embreagem (vida útil reduzida)
4. Agenda manutenção preventiva

**Valor:** Redução de 25% em quebras inesperadas

### 5.4 Route Optimization

#### UC-06: Safe Route Recommendation

**Ator:** Despachante

**Fluxo:**
1. Ao planejar rota, sistema analisa histórico
2. Identifica: Rota A tem 3x mais frenagens bruscas que Rota B
3. Sugere Rota B (mesmo que 5km mais longa)
4. Justifica: menor risco, menor consumo, menor desgaste

**Valor:** Segurança > Distância

---

## 6. Technical Implementation Roadmap

### Phase 1: Foundation (Semanas 1-2)

**Objetivos:**
- ✅ Database schema criado
- ✅ Event detection básico funcionando
- ✅ API endpoints implementados

**Tarefas:**
1. **DB Schema** (2 dias)
   - Criar tabelas vehicle_events, vehicle_scores, trips, gamification
   - Migrations SQL
   - Testes de integridade referencial

2. **Behavioral Engine** (3 dias)
   - Implementar `behavioral_engine.py`
   - Algoritmos de detecção de eventos
   - Cálculo de scores

3. **API Endpoints** (3 dias)
   - `GET /api/vehicles/<id>/score`
   - `GET /api/vehicles/<id>/events`
   - `GET /api/fleet/leaderboard`
   - `POST /api/events` (internal)

4. **Simulator Enhancement** (2 dias)
   - Adicionar geração de eventos
   - Scores variáveis por veículo
   - Testes de carga

**Entregáveis:**
- Database funcional com eventos sendo gravados
- API retornando dados corretos
- Simulador gerando eventos realistas

### Phase 2: Core Features (Semanas 3-5)

**Objetivos:**
- ✅ Frontend exibindo scores
- ✅ Marcadores color-coded
- ✅ Dashboard comportamental básico

**Tarefas:**
1. **Vehicle Markers** (2 dias)
   - Color-coding por score
   - Popup enriquecido
   - Animações de transição

2. **Event Markers** (2 dias)
   - Ícones por tipo de evento
   - Popup com detalhes
   - Filtros de visualização

3. **Behavioral Dashboard** (5 dias)
   - Fleet overview cards
   - Score distribution chart
   - Real-time alerts panel
   - Leaderboard component

4. **Real-time Updates** (3 dias)
   - WebSocket integration
   - Event streaming
   - Score updates ao vivo

**Entregáveis:**
- Mapa visualmente aprimorado
- Dashboard funcional
- Alertas em tempo real

### Phase 3: Advanced Analytics (Semanas 6-9)

**Objetivos:**
- ✅ Análise temporal
- ✅ Insights preditivos
- ✅ Coaching recommendations

**Tarefas:**
1. **Temporal Analysis** (4 dias)
   - Event timeline component
   - Route playback com eventos
   - Score evolution charts

2. **Predictive Insights** (5 dias)
   - ML model treinado em dados históricos
   - Predição de risco futuro
   - Recomendações de manutenção

3. **Coaching Module** (4 dias)
   - Identificação de padrões
   - Sugestões personalizadas
   - Tracking de melhoria

4. **Reports Generator** (3 dias)
   - Relatórios semanais/mensais
   - Export PDF
   - Scheduled emails

**Entregáveis:**
- Analytics avançado
- Sistema de coaching
- Relatórios automáticos

### Phase 4: Gamification (Semanas 10-11)

**Objetivos:**
- ✅ Sistema de pontos
- ✅ Conquistas
- ✅ Desafios

**Tarefas:**
1. **Points System** (2 dias)
   - Acúmulo de pontos
   - Regras de bonificação
   - Histórico

2. **Achievements** (3 dias)
   - Badge design
   - Trigger system
   - Rarity levels

3. **Challenges** (3 dias)
   - Weekly challenges
   - Progress tracking
   - Leaderboard

4. **Rewards** (2 dias)
   - Redemption system
   - Partner integration
   - Notification system

**Entregáveis:**
- Gamificação completa
- Engajamento de motoristas

### Phase 5: Integration & Testing (Semanas 12-13)

**Objetivos:**
- ✅ Testes end-to-end
- ✅ Otimização de performance
- ✅ Documentação completa

**Tarefas:**
1. **Testing** (4 dias)
   - Unit tests (backend)
   - Integration tests
   - E2E tests (frontend)
   - Load testing

2. **Performance** (3 dias)
   - Query optimization
   - Caching layer
   - CDN setup

3. **Documentation** (3 dias)
   - API docs (Swagger)
   - User manual
   - Admin guide

**Entregáveis:**
- Sistema production-ready
- Documentação completa

---

## 7. Data Flow Diagrams

### 7.1 Current AITrack Data Flow

```
Tracker Device
     │
     │ TCP (raw packet)
     ▼
Socket Server (port 9000)
     │
     │ decode
     ▼
Protocol Parser
     │
     │ {device_id, lat, lon, speed, heading, timestamp}
     ▼
DB Handler
     │
     │ INSERT INTO localizacao
     ▼
MySQL (tracker)
     │
     │ SELECT latest positions
     ▼
REST API (port 5000)
     │
     │ JSON response
     ▼
Frontend (React)
     │
     │ render
     ▼
Leaflet Map (vehicle markers)
```

### 7.2 Enhanced Data Flow (with DataDrivr)

```
Tracker Device
     │
     │ TCP (raw packet)
     ▼
Socket Server (port 9000)
     │
     │ decode
     ▼
Protocol Parser
     │
     ├──────────────────────────────┐
     │                              │
     │ {standard GPS data}          │ {speed, heading, timestamp history}
     ▼                              ▼
DB Handler                    Behavioral Engine
     │                              │
     │                              │ detect_events()
     │                              │ calculate_score()
     │                              │
     │                              ▼
     │                         Event Detected?
     │                              │
     │                         YES  │  NO
     │                         ┌────┴────┐
     │                         ▼         │
     │                    vehicle_events │
     │                         │         │
     │                         ▼         │
     │                    update_score   │
     │                         │         │
     │                         ▼         │
     │                    vehicle_scores │
     │                         │         │
     ├─────────────────────────┴─────────┘
     │
     │ INSERT INTO localizacao + events + scores
     ▼
MySQL (tracker)
     │
     ├───────────────────┬──────────────────┐
     │                   │                  │
     │ positions         │ events           │ scores
     ▼                   ▼                  ▼
REST API (port 5000)
     │
     ├─────────────────────┬────────────────┬────────────────┐
     │                     │                │                │
     │ /api/positions      │ /api/events    │ /api/scores    │ /api/leaderboard
     ▼                     ▼                ▼                ▼
Frontend (React)
     │
     ├──────────────────────┬───────────────┬──────────────┐
     │                      │               │              │
     │ Map Component        │ Dashboard     │ Alerts       │ Leaderboard
     ▼                      ▼               ▼              ▼
Color-coded markers    Score charts    Real-time alerts  Ranking
Event markers          KPI cards       Notifications     Achievements
```

### 7.3 Event Detection Pipeline

```
GPS Data Stream (1 Hz)
     │
     ▼
[ Buffer: Last 5 seconds of data ]
     │
     ├─────────────┬─────────────┬─────────────┬─────────────┐
     │             │             │             │             │
     ▼             ▼             ▼             ▼             ▼
Speed Delta   Heading Delta   Location      Timestamp    Pattern
Analysis      Analysis        Context       Consistency  Recognition
     │             │             │             │             │
     ▼             ▼             ▼             ▼             ▼
Harsh Accel?  Sharp Turn?   Urban/Highway? Valid data?  Fatigue?
Harsh Brake?                 Speed limit                 Distraction?
Speeding?
     │             │             │             │             │
     └─────────────┴─────────────┴─────────────┴─────────────┘
                            │
                            ▼
                    Event Classifier
                            │
                    ┌───────┴────────┐
                    │                │
               Event Found?      No Event
                    │                │
                    ▼                ▼
            Severity Assessment   Continue
                    │
                    ├─────────┬─────────┬─────────┐
                    │         │         │         │
                    ▼         ▼         ▼         ▼
                  Low     Medium     High    Critical
                    │         │         │         │
                    └─────────┴─────────┴─────────┘
                                │
                                ▼
                        Store in DB + Trigger Alert
```

### 7.4 Scoring Calculation Workflow

```
Vehicle Trip Data
     │
     ▼
Fetch Events (last 24h / 7d / 30d)
     │
     ├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
     │          │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼          ▼
Speed      Accel      Brake     Cornering  Distraction  Time    Fatigue
Violations  Events     Events    Events     Events      Factor  Factor
     │          │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼          ▼
Count &    Count &    Count &   Count &   Count &    Night   Long
Duration   Severity   Severity  Severity   Duration   Driving  Trips
     │          │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼          ▼
Score     Score      Score     Score      Score      Score    Score
Speed     Accel      Brake     Corner     Distract   Time     Fatigue
(0-100)   (0-100)    (0-100)   (0-100)    (0-100)    (0-100)  (0-100)
     │          │          │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
                                │
                                ▼
                    Weighted Average Formula
                                │
            Overall Score = 0.25×Speed + 0.20×Accel + 0.20×Brake +
                           0.15×Corner + 0.10×Distract + 0.05×Time + 0.05×Fatigue
                                │
                                ▼
                        Store in vehicle_scores
                                │
                                ▼
                        Update Frontend + Alerts
```

---

## 8. API Specifications

### 8.1 New Endpoints

#### GET /api/vehicles/{device_id}/score

**Description:** Retorna o score comportamental atual de um veículo

**Response:**
```json
{
  "device_id": "SIM-1000",
  "overall_score": 78.5,
  "scores": {
    "speed": 85.0,
    "acceleration": 72.0,
    "braking": 80.0,
    "cornering": 75.0,
    "distraction": 90.0,
    "time_of_day": 70.0,
    "fatigue": 85.0
  },
  "trip_count": 45,
  "total_distance_km": 1250.3,
  "total_duration_hours": 32.5,
  "last_updated": "2026-01-27T15:30:00Z"
}
```

#### GET /api/vehicles/{device_id}/events

**Description:** Retorna eventos comportamentais de um veículo

**Query Parameters:**
- `limit` (default: 50)
- `since` (ISO timestamp)
- `type` (harsh_accel, harsh_brake, speeding, sharp_turn)
- `severity` (low, medium, high, critical)

**Response:**
```json
{
  "device_id": "SIM-1000",
  "events": [
    {
      "id": 1234,
      "type": "harsh_brake",
      "severity": "high",
      "timestamp": "2026-01-27T15:25:30Z",
      "location": {
        "latitude": -23.5505,
        "longitude": -46.6333
      },
      "speed": 65.0,
      "score_impact": -5,
      "metadata": {
        "deceleration": 3.2
      }
    }
  ],
  "total_count": 127
}
```

#### GET /api/fleet/leaderboard

**Description:** Ranking de veículos por score

**Query Parameters:**
- `timeframe` (24h, 7d, 30d, all)
- `limit` (default: 10)
- `order` (asc, desc)

**Response:**
```json
{
  "timeframe": "7d",
  "leaderboard": [
    {
      "rank": 1,
      "device_id": "SIM-1005",
      "vehicle_plate": "ABC-1234",
      "driver_name": "João Silva",
      "score": 92.3,
      "events_count": 2,
      "distance_km": 450.2,
      "trips": 15
    },
    {
      "rank": 2,
      "device_id": "SIM-1003",
      "vehicle_plate": "XYZ-5678",
      "driver_name": "Maria Santos",
      "score": 88.7,
      "events_count": 5,
      "distance_km": 380.1,
      "trips": 12
    }
  ],
  "fleet_average": 75.4,
  "total_vehicles": 50
}
```

#### POST /api/events (Internal)

**Description:** Endpoint interno para registrar eventos

**Request:**
```json
{
  "device_id": "SIM-1000",
  "event_type": "harsh_brake",
  "severity": "high",
  "timestamp": "2026-01-27T15:25:30Z",
  "latitude": -23.5505,
  "longitude": -46.6333,
  "speed": 65.0,
  "heading": 180,
  "metadata": {
    "deceleration": 3.2,
    "previous_speed": 85.0
  }
}
```

**Response:**
```json
{
  "event_id": 1234,
  "status": "recorded",
  "score_impact": -5,
  "new_overall_score": 73.5
}
```

### 8.2 WebSocket Events

**Connection:** `ws://localhost:5000/ws/realtime`

**Event Types:**

**1. New Position**
```json
{
  "type": "position_update",
  "device_id": "SIM-1000",
  "latitude": -23.5505,
  "longitude": -46.6333,
  "speed": 65.0,
  "heading": 180,
  "score": 78.5,
  "timestamp": "2026-01-27T15:30:00Z"
}
```

**2. Behavioral Event**
```json
{
  "type": "behavioral_event",
  "device_id": "SIM-1000",
  "event": {
    "id": 1234,
    "type": "harsh_brake",
    "severity": "high",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "timestamp": "2026-01-27T15:25:30Z"
  }
}
```

**3. Score Update**
```json
{
  "type": "score_update",
  "device_id": "SIM-1000",
  "overall_score": 73.5,
  "previous_score": 78.5,
  "change": -5.0
}
```

---

## 9. Security & Privacy Considerations

### 9.1 LGPD Compliance

**Dados Pessoais Coletados:**
- Localização GPS (dado sensível)
- Padrões de comportamento de motoristas
- Identificação de veículos/motoristas

**Medidas de Proteção:**
1. **Consentimento:** Termo de aceite explícito antes de coletar dados
2. **Anonimização:** Opção de exibir apenas device_id (não nome de motorista)
3. **Direito ao Esquecimento:** API para deletar dados de motorista
4. **Transparência:** Dashboard mostrando quais dados são coletados
5. **Finalidade:** Uso restrito a gestão de frota e seguros

### 9.2 Access Control

**Níveis de Acesso:**

| Papel | Permissões |
|-------|------------|
| Admin | Full access (todos veículos, todas funcionalidades) |
| Fleet Manager | View all vehicles, generate reports, configure alerts |
| Driver | View only own vehicle data, own scores, own achievements |
| Insurance Partner | Read-only access via API (aggregated scores only) |

**Autenticação:**
- JWT tokens com expiração
- Role-based access control (RBAC)
- API keys para integrações

### 9.3 Audit Logging

**Eventos Auditados:**
- Login/logout
- Acesso a dados de motoristas
- Alterações de configuração
- Export de relatórios
- Compartilhamento de dados com terceiros

**Log Format:**
```json
{
  "timestamp": "2026-01-27T15:30:00Z",
  "user_id": "admin@company.com",
  "action": "view_driver_events",
  "resource": "device:SIM-1000",
  "ip_address": "192.168.1.10",
  "result": "success"
}
```

---

## 10. Performance Considerations

### 10.1 Real-time Processing Requirements

**Latência Máxima:**
- Event detection: < 500ms
- Score update: < 1s
- Frontend update: < 2s

**Throughput:**
- 1000 vehicles simultâneos
- 1 update/second por veículo
- 1000 eventos/segundo no pico

### 10.2 Database Optimization

**Índices Críticos:**
```sql
-- Para queries de eventos recentes
CREATE INDEX idx_events_device_time ON vehicle_events(device_id, timestamp DESC);

-- Para leaderboard
CREATE INDEX idx_scores_overall ON vehicle_scores(score_overall DESC);

-- Para análise temporal
CREATE INDEX idx_events_type_time ON vehicle_events(event_type, timestamp);
```

**Particionamento:**
```sql
-- Particionar eventos por mês (retenção de 12 meses)
ALTER TABLE vehicle_events PARTITION BY RANGE (YEAR(timestamp)*100 + MONTH(timestamp)) (
    PARTITION p202601 VALUES LESS THAN (202602),
    PARTITION p202602 VALUES LESS THAN (202603),
    ...
);
```

### 10.3 Caching Strategy

**Redis Cache:**
```python
# Cache de scores (TTL: 60s)
cache_key = f"vehicle_score:{device_id}"
score = redis.get(cache_key)
if not score:
    score = calculate_score_from_db(device_id)
    redis.setex(cache_key, 60, score)

# Cache de leaderboard (TTL: 300s)
cache_key = f"leaderboard:{timeframe}"
leaderboard = redis.get(cache_key)
if not leaderboard:
    leaderboard = query_leaderboard_from_db(timeframe)
    redis.setex(cache_key, 300, leaderboard)
```

### 10.4 Scalability

**Horizontal Scaling:**
- Load balancer (Nginx) para múltiplas instâncias da API
- Stateless API (JWT auth)
- Database read replicas para queries pesadas

**Message Queue:**
- RabbitMQ/Kafka para processamento assíncrono de eventos
- Workers dedicados para cálculo de scores

---

## 11. Future Enhancements

### 11.1 Machine Learning Integration

**Predictive Risk Scoring:**
- Treinar modelo ML em dados históricos (eventos → acidentes)
- Predizer probabilidade de acidente nos próximos 7 dias
- Features: score history, event frequency, time patterns

**Anomaly Detection:**
- Detectar mudanças súbitas de comportamento (possível furto, saúde do motorista)
- Alertas automáticos para desvios estatísticos

### 11.2 Insurance API Integration

**Partner APIs:**
- Porto Seguro Telemática API
- Liberty Seguros Drive Well API
- HDI Seguros SmartDrive API

**Fluxo:**
1. AITrack calcula scores mensais
2. API push para seguradora
3. Seguradora ajusta prêmio
4. Notificação para cliente

### 11.3 Mobile App for Drivers

**Features:**
- Ver score em tempo real
- Histórico de viagens com notas
- Dicas de melhoria personalizadas
- Conquistas e ranking
- Notificações de alertas

### 11.4 Advanced Fraud Detection

**Padrões Suspeitos:**
- Sinistro reportado sem eventos registrados
- Mudança brusca de comportamento antes do sinistro
- Desconexão do tracker antes do evento
- Localização inconsistente com rota declarada

### 11.5 Route Recommendation Engine

**Algoritmo:**
1. Mapear histórico de eventos por segmento de rota
2. Calcular "risk score" por rota
3. Sugerir rotas alternativas mais seguras
4. Considerar trade-off: distância vs segurança

---

## 12. Plano de Demonstração (90 minutos)

### Minuto 0-10: Setup

```bash
# Clone e setup
cd /home/pasteurjr/progreact/aitrack
git checkout -b feature/datadrivr-integration

# Verificar ambiente
python --version  # 3.9+
node --version    # 16+
mysql --version   # 5.7+
```

### Minuto 10-30: Simulator Enhancement

**Arquivo: `simulator.py`**

Adicionar classe para gerar eventos:

```python
class BehavioralVehicle(Vehicle):
    def __init__(self, device_id, protocol, route_coords, driver_profile):
        super().__init__(device_id, protocol, route_coords)
        self.driver_profile = driver_profile  # 'good', 'moderate', 'poor'
        self.score = self._initial_score()
        self.last_speed = 0

    def _initial_score(self):
        if self.driver_profile == 'good':
            return random.uniform(80, 95)
        elif self.driver_profile == 'moderate':
            return random.uniform(60, 79)
        else:
            return random.uniform(30, 59)

    def generate_events(self, speed):
        events = []

        # Harsh acceleration
        if self.driver_profile == 'poor' and random.random() < 0.1:
            events.append('harsh_accel')
            self.score -= 2

        # Harsh braking
        if self.driver_profile != 'good' and random.random() < 0.08:
            events.append('harsh_brake')
            self.score -= 3

        # Speeding
        if speed > 80 and random.random() < 0.15:
            events.append('speeding')
            self.score -= 1

        self.score = max(0, min(100, self.score))
        return events
```

**Teste:**
```bash
python simulator.py
# Verificar console logs com eventos
```

### Minuto 30-50: Backend

**1. DB Migration (5 min)**
```bash
mysql -u root -p tracker < migrations/add_behavioral_tables.sql
```

**2. API Endpoints (15 min)**

Arquivo: `server/api.py`

```python
@app.route('/api/vehicles/<device_id>/score')
def get_vehicle_score(device_id):
    # Query from vehicle_scores
    # Return JSON
    pass

@app.route('/api/fleet/leaderboard')
def get_leaderboard():
    # Query top 10 by score
    # Return JSON
    pass
```

**Teste:**
```bash
curl http://localhost:5000/api/vehicles/SIM-1000/score
```

### Minuto 50-90: Frontend

**1. Color-coded Markers (10 min)**

Arquivo: `frontend/src/components/MapComponent.tsx`

```typescript
const getMarkerStyle = (score: number) => {
  const color = score >= 75 ? 'green' : score >= 50 ? 'orange' : 'red';
  return `background-color: ${color}; ...`;
};
```

**2. Simple Dashboard (20 min)**

Arquivo: `frontend/src/components/BehavioralDashboard.tsx`

```typescript
export const BehavioralDashboard = () => {
  const [scores, setScores] = useState([]);

  useEffect(() => {
    fetch('/api/fleet/leaderboard')
      .then(res => res.json())
      .then(data => setScores(data.leaderboard));
  }, []);

  const fleetAvg = scores.reduce((sum, s) => sum + s.score, 0) / scores.length;

  return (
    <div className="dashboard">
      <h2>Fleet Overview</h2>
      <div>Average Score: {fleetAvg.toFixed(1)}</div>
      <div>Top Performer: {scores[0]?.driver_name} ({scores[0]?.score})</div>
    </div>
  );
};
```

**3. Integration (10 min)**

Arquivo: `frontend/src/App.tsx`

```typescript
import { BehavioralDashboard } from './components/BehavioralDashboard';

function App() {
  return (
    <div>
      <BehavioralDashboard />
      <MapComponent />
    </div>
  );
}
```

### Demo Final (Minuto 90)

**Demonstração:**
1. Iniciar simulador → 10 veículos com perfis variados
2. Abrir frontend → Ver marcadores coloridos
3. Clicar em veículo vermelho → Mostrar score baixo
4. Ver dashboard → Fleet average, top 3, bottom 3
5. Aguardar evento → Alerta aparece

**Resultado Esperado:**
- ✅ Marcadores coloridos no mapa
- ✅ Dashboard com métricas de frota
- ✅ Scores variando por veículo
- ✅ Simulador gerando eventos

---

## Anexos

### A. Glossário

- **Behavioral Scoring:** Sistema de pontuação (0-100) baseado em métricas de direção
- **Event Detection:** Identificação automática de comportamentos de risco
- **Harsh Acceleration:** Aceleração brusca (> 2 m/s²)
- **Harsh Braking:** Frenagem brusca (> 3 m/s²)
- **Telematics:** Combinação de telecomunicações + informática para rastreamento
- **PHYD:** Pay-How-You-Drive (seguro baseado em comportamento)

### B. Referências

- DataDrivr Mobile App: `/home/pasteurjr/progreact/datadrivr/mobile-app`
- DataDrivr Insurance Web: `/home/pasteurjr/progreact/datadrivr/insurance-web`
- AITrack: `/home/pasteurjr/progreact/aitrack`
- Dirijabem Database: `README_DIRIJABEM.md`

---

**Documento gerado em:** 2026-01-27
**Versão:** 1.0
**Autor:** Claude (Anthropic) + Pasteur Jr
**Status:** Pronto para Implementação
