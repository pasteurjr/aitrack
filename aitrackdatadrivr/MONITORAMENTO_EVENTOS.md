# Sistema de Monitoramento de Eventos - AITrack DataDrivr

## Índice
1. [Arquitetura: Polling vs Pub/Sub](#arquitetura-polling-vs-pubsub)
2. [Classificação Completa de Eventos](#classificação-completa-de-eventos)
3. [Arquitetura de Detecção](#arquitetura-de-detecção)
4. [Análise de Latência](#análise-de-latência)
5. [Schema do Banco de Dados](#schema-do-banco-de-dados)
6. [Roadmap de Implementação](#roadmap-de-implementação)
7. [Status Atual do Sistema](#status-atual-do-sistema)

---

## Arquitetura: Polling vs Pub/Sub

### Diferença Fundamental: PULL vs PUSH

#### **Polling (PULL)** - Você pergunta repetidamente
```
Monitor: "Tem novidade?"
Sistema: "Não."
[aguarda 5 segundos]

Monitor: "E agora?"
Sistema: "Não."
[aguarda 5 segundos]

[EVENTO CRÍTICO ACONTECE às 10:30:42]
[mas monitor só vai perguntar de novo às 10:30:45]

Monitor: "Tem?"
Sistema: "SIM! Aconteceu há 3 segundos"
└─> Atraso de 3 segundos
```

**Analogia:** Você fica perguntando ao correio "Chegou carta? Chegou carta?"

---

#### **Pub/Sub (PUSH)** - Sistema te avisa na hora
```
Monitor: [conectado, esperando em blocked I/O...]

[EVENTO CRÍTICO ACONTECE às 10:30:42]

Sistema: "NOVO EVENTO!" → Monitor recebe INSTANTANEAMENTE
└─> Atraso de ~10 milissegundos
```

**Analogia:** O correio **te liga** quando chega carta

---

### Como Funciona por Baixo (TCP/IP)

#### **MySQL Polling = Múltiplas Conexões Curtas**
```
Cliente                    MySQL
   │                          │
   │─── Abre conexão ────────>│
   │─── SELECT * FROM... ────>│
   │<──── Resultado ──────────┤
   │─── Fecha conexão ────────│
   │                          │
   │ time.sleep(5) 😴         │
   │                          │
   │─── Abre conexão ────────>│  ← Overhead: abrir/fechar repetido
   │─── SELECT * FROM... ────>│
   │<──── Resultado ──────────┤
```

**Overhead:** Abrir/fechar conexão consome CPU e tempo

---

#### **Redis Pub/Sub = 1 Conexão Persistente**
```
Cliente                    Redis
   │                          │
   │─── SUBSCRIBE events ────>│
   │                          │ ← Conexão fica aberta
   │ [bloqueado esperando...] │
   │                          │
   │                          │ [evento acontece]
   │<──── PUSH mensagem ──────┤ ← Servidor EMPURRA dados
   │ [processa]               │
   │ [bloqueado esperando...] │
```

**Eficiência:** Sem overhead, servidor avisa quando há novidade

---

### Comparação Técnica

| Aspecto | MySQL Polling | Redis Pub/Sub |
|---------|---------------|---------------|
| **Padrão** | PULL (você pergunta) | PUSH (te avisam) |
| **Conexão** | Abre/fecha toda hora | Persistente |
| **Latência média** | 2-5 segundos | 10-50ms |
| **Pior caso** | 1 intervalo completo | Latência de rede |
| **Overhead CPU** | Alto (queries repetidas) | Baixo (blocked I/O) |
| **Detecta evento em** | Próxima query | Instantaneamente |
| **Uso no sistema** | Eventos comportamentais | Eventos críticos |

---

### Exemplo de Código

#### **MySQL Polling (Atual no Frontend)**
```python
# ❌ Faz requisições repetidas
while True:
    # 1. Abre conexão
    eventos = db.query("SELECT * FROM eventos WHERE processado = 0")

    # 2. Processa
    for evento in eventos:
        processar(evento)

    # 3. AGUARDA 5 SEGUNDOS fazendo NADA
    time.sleep(5)  # ← Período morto
```

**Problema:** Durante os 5s de sleep, você está **CEGO** para eventos críticos.

---

#### **Redis Pub/Sub**
```python
# ✅ Recebe notificação push em tempo real
redis_client = redis.Redis()
pubsub = redis_client.pubsub()
pubsub.subscribe('vehicle.events')  # Abre conexão UMA vez

# Loop BLOQUEANTE - não é polling!
for message in pubsub.listen():  # ← Blocked I/O, acorda quando chega mensagem
    evento = json.loads(message['data'])
    processar(evento)  # Executa IMEDIATAMENTE
```

**Vantagem:** `listen()` **bloqueia** a thread até chegar mensagem (não consome CPU).

---

## Classificação Completa de Eventos

### 🚨 EVENTOS CRÍTICOS (8 eventos)
**Tecnologia:** Redis Pub/Sub
**SLA:** Resposta < 30 segundos
**Por quê?** Segurança patrimonial, risco de roubo, socorro urgente, perda de rastreamento

| # | Código | Nome | Severidade | Tempo | Status |
|---|--------|------|------------|-------|--------|
| 1 | `panic_button` | Botão de Pânico | 🔴 CRITICAL | <10s | ⚠️ A CRIAR |
| 2 | `geofence_exit` | Saída de Cerca | 🔴 CRITICAL | <30s | ⚠️ A CRIAR |
| 3 | `geofence_entry` | Entrada em Área Proibida | 🔴 CRITICAL | <30s | ⚠️ A CRIAR |
| 4 | `tamper_detected` | Adulteração do Rastreador | 🔴 CRITICAL | <15s | ⚠️ A CRIAR |
| 5 | `theft_suspected` | Suspeita de Roubo | 🔴 CRITICAL | <30s | ⚠️ A CRIAR |
| 6 | `collision_detected` | Colisão Detectada | 🔴 CRITICAL | <30s | ⚠️ A CRIAR |
| 7 | `towing_detected` | Reboque Não Autorizado | 🟠 HIGH | <60s | ⚠️ A CRIAR |
| 8 | `unusual_hours` | Uso Fora de Horário | 🔴 CRITICAL | <30s | ⚠️ A CRIAR |

#### Detalhamento dos Eventos Críticos

**1. panic_button** (Botão de Pânico)
- **Descrição:** Motorista acionou botão SOS
- **Detecção:** Bit/flag no pacote GPS (Maxtrack, Suntech, Queclink)
- **Ação:** Notificar central + polícia + proprietário
- **Dados:** `{timestamp, lat, lon, speed, vehicle_id}`

**2. geofence_exit** (Saída de Cerca Virtual)
- **Descrição:** Veículo saiu de área autorizada (residência, garagem, empresa)
- **Detecção:** Coordenadas fora de polígono ou raio circular
- **Ação:** Alerta proprietário, verificar autorização
- **Dados:** `{fence_id, fence_name, timestamp, lat, lon, distance_from_fence_meters}`
- **Tabela requerida:** `cercas`, `veiculo_cercas`

**3. geofence_entry** (Entrada em Área Proibida)
- **Descrição:** Veículo entrou em área de risco (desmanche, favela perigosa)
- **Detecção:** Coordenadas dentro de polígono de área de risco
- **Ação:** Alerta crítico, possível roubo em andamento
- **Dados:** `{fence_id, fence_name, risk_level, timestamp, lat, lon}`

**4. tamper_detected** (Adulteração do Rastreador)
- **Descrição:** Tentativa de desligar/remover rastreador
- **Detecção:** Múltiplos sinais anormais
- **Subtipos:**
  - `main_power_cut` - Bateria principal desconectada
  - `gps_antenna_disconnected` - Antena GPS cortada
  - `signal_loss` - Sem comunicação há >10 minutos
  - `gps_jamming` - Bloqueador de GPS detectado (sem fix com sinais fortes)
- **Ação:** Alerta crítico, possível roubo
- **Dados:** `{tamper_types[], last_known_location, time_since_last_signal}`

**5. theft_suspected** (Suspeita de Roubo)
- **Descrição:** Correlação de múltiplos indicadores de roubo
- **Detecção:** TheftAgent analisa padrão
- **Indicadores:**
  - Movimento fora de horário habitual (2-6 AM)
  - Saída de cerca + ignição sem motorista autorizado
  - Alta velocidade após pânico/tamper
  - Direção para área de desmanche conhecida
- **Ação:** Bloquear veículo (se possível), acionar polícia
- **Dados:** `{confidence_score, indicators[], related_events[]}`

**6. collision_detected** (Colisão Detectada)
- **Descrição:** Impacto forte detectado por acelerômetro
- **Detecção:** G-force > 4G em qualquer eixo
- **Ação:** Verificar se precisa socorro
- **Dados:** `{impact_force_g, speed_before, speed_after, lat, lon}`
- **Requer:** Acelerômetro 3 eixos no rastreador

**7. towing_detected** (Reboque Detectado)
- **Descrição:** Movimento sem ignição ligada
- **Detecção:** GPS detecta movimento >1 km com ignição OFF
- **Ação:** Possível reboque não autorizado ou roubo
- **Dados:** `{distance_moved_km, speed, ignition_status, duration}`

**8. unusual_hours** (Uso Fora de Horário) ⚠️ RECLASSIFICADO
- **Descrição:** Movimento em horário não habitual para aquele veículo
- **Detecção:** Padrão de uso histórico (ML ou regra simples)
- **Exemplo:** Veículo que sempre fica parado 22h-6h se move às 3h
- **Por que CRITICAL?** Forte indicador de roubo (motorista dormindo, veículo se movendo)
- **Ação:** Verificar imediatamente se é autorizado, possível roubo em andamento
- **Dados:** `{usual_hours, detected_time, deviation_hours, movement_speed}`
- **Custo do atraso:** 30min = veículo pode estar desmanchado

---

### ⚠️ EVENTOS COMPORTAMENTAIS (10 eventos)
**Tecnologia:** MySQL Polling
**SLA:** Resposta de 1-15 minutos
**Por quê?** Padrão inadequado que gera custo/risco, mas não é emergência

| # | Código | Nome | Severidade | Tempo | Status |
|---|--------|------|------------|-------|--------|
| 9 | `harsh_brake` | Frenagem Brusca | 🟡 MEDIUM | 1-5min | ✅ EXISTE |
| 10 | `harsh_accel` | Aceleração Brusca | 🟡 MEDIUM | 1-5min | ✅ EXISTE |
| 11 | `speeding` | Excesso de Velocidade | 🟡 MEDIUM | 1-5min | ✅ EXISTE |
| 12 | `sharp_turn` | Curva Fechada | 🟡 MEDIUM | 1-5min | ✅ EXISTE |
| 13 | `fatigue_suspected` | Fadiga Detectada | 🟠 HIGH | 5-15min | ⚠️ A CRIAR |
| 14 | `distracted_driving` | Direção Distraída | 🟠 HIGH | 5-10min | ⚠️ A CRIAR |
| 15 | `aggressive_driving` | Direção Agressiva | 🟠 HIGH | 10-15min | ⚠️ A CRIAR |
| 16 | `excessive_idle` | Tempo Ocioso Excessivo | 🟡 MEDIUM | 5-10min | ⚠️ A CRIAR |
| 17 | `route_deviation` | Desvio de Rota | 🟡 MEDIUM | 1-3min | ⚠️ A CRIAR |
| 18 | `low_battery` | Bateria Fraca | 🟠 HIGH | 15-30min | ⚠️ A CRIAR |

#### Detalhamento dos Eventos Comportamentais

**8. harsh_brake** ✅ (Frenagem Brusca)
- **Descrição:** Desaceleração > 20 km/h em <3 segundos
- **Detecção:** `behavioral_engine.py` - `HARSH_BRAKE_THRESHOLD = 20.0`
- **Impacto score:** -2 pontos
- **Dados:** `{speed_before, speed_after, deceleration_kmh_s, lat, lon, timestamp}`

**9. harsh_accel** ✅ (Aceleração Brusca)
- **Descrição:** Aceleração > 15 km/h em <3 segundos
- **Detecção:** `behavioral_engine.py` - `HARSH_ACCEL_THRESHOLD = 15.0`
- **Impacto score:** -1 ponto
- **Dados:** `{speed_before, speed_after, acceleration_kmh_s, lat, lon, timestamp}`

**10. speeding** ✅ (Excesso de Velocidade)
- **Descrição:** Velocidade acima do limite da via
- **Detecção:** `behavioral_engine.py` - `SPEEDING_THRESHOLD = 80.0` (configurável)
- **Impacto score:** -3 pontos
- **Fuzzy:** Contribui para OST (tempo), OSA (média), OSP (pico)
- **Dados:** `{speed, limit, excess, duration, lat, lon}`

**11. sharp_turn** ✅ (Curva Fechada)
- **Descrição:** Mudança de direção > 45° em <5 segundos
- **Detecção:** `behavioral_engine.py` - bearing change
- **Impacto score:** -2 pontos
- **Fuzzy:** Contribui para BRP (pico), BRM (moderada), BRA (agressiva)
- **Dados:** `{bearing_before, bearing_after, angle_change, speed, lat, lon}`

**12. fatigue_suspected** (Fadiga Detectada)
- **Descrição:** Aumento de eventos + micro-correções ao longo do tempo
- **Detecção:** Análise temporal de padrões
- **Indicadores:**
  - Taxa de eventos dobrou em 90 minutos
  - Múltiplos sharp_turn pequenos (<20°) sugerindo lane drift
  - Direção contínua >4 horas sem parada
- **Ação:** Sugerir parada para descanso
- **Dados:** `{event_rate_increase, continuous_driving_hours, micro_corrections_count}`

**13. distracted_driving** (Direção Distraída)
- **Descrição:** Padrão errático indicando falta de atenção
- **Detecção:** Análise de variação de velocidade e direção
- **Indicadores:**
  - Velocidade oscilando (+/-10 km/h a cada 30s)
  - Sharp turns frequentes mas pequenos
  - Acelerações/frenagens desnecessárias
- **Ação:** Alerta para prestar atenção na direção
- **Dados:** `{speed_variation_stddev, turn_frequency, acceleration_frequency}`

**15. aggressive_driving** (Direção Agressiva)
- **Descrição:** Score fuzzy < 50 (categoria AGRESSIVO)
- **Detecção:** Sistema fuzzy `driverprofile.fcl` PERFIL > 75
- **Critérios:** Múltiplas regras fuzzy ativadas (speeding + harsh events + turns)
- **Ação:** Coaching, treinamento obrigatório
- **Dados:** `{fuzzy_score, perfil_category, dominant_rule_cluster}`

**16. excessive_idle** (Tempo Ocioso Excessivo) ⚠️ RECLASSIFICADO
- **Descrição:** Motor ligado parado >15 minutos
- **Detecção:** Ignição ON + velocidade 0 + tempo >15min
- **Por que BEHAVIORAL?** Padrão de uso inadequado com custo direto
- **Impacto:** Desperdício de ~0.8L/hora = R$5-10/hora
- **Ação:** Alerta para desligar motor, treinar motorista
- **Dados:** `{idle_duration_minutes, fuel_wasted_liters_estimated, lat, lon}`
- **Tempo resposta:** 5-10min (não precisa ser instantâneo, mas deve alertar rápido)

**17. route_deviation** (Desvio de Rota) ⚠️ RECLASSIFICADO
- **Descrição:** Veículo fora da rota planejada
- **Detecção:** Distância > 500m do trajeto esperado
- **Por que BEHAVIORAL?** Pode indicar uso não autorizado ou ineficiência
- **Severidade variável:** MEDIUM (geral) → HIGH (transporte de valores)
- **Ação:** Notificar gestor, verificar autorização
- **Dados:** `{planned_route_id, deviation_distance_km, extra_time_minutes, current_location}`
- **Requer:** Tabela `rotas_planejadas`
- **Tempo resposta:** 1-3min (quanto antes detectar, menor o desvio)

**18. low_battery** (Bateria Fraca) ⚠️ RECLASSIFICADO
- **Descrição:** Bateria do rastreador <20%
- **Detecção:** Campo `battery_voltage` ou `battery_percent` do GPS
- **Por que BEHAVIORAL?** Risco de perder rastreamento, requer ação preventiva
- **Ação:** Carregar/trocar bateria backup URGENTE
- **Dados:** `{battery_voltage, battery_percent, estimated_hours_remaining}`
- **Tempo resposta:** 15-30min (antes que acabe completamente)
- **Custo do atraso:** Perder rastreamento = não detectar roubo

---

### 📊 EVENTOS OPERACIONAIS (2 eventos)
**Tecnologia:** MySQL Polling
**SLA:** Resposta de 1-24 horas
**Por quê?** Análise agregada, manutenção preventiva, não urgente

| # | Código | Nome | Severidade | Tempo | Status |
|---|--------|------|------------|-------|--------|
| 19 | `fuel_waste_detected` | Desperdício de Combustível | 🟢 LOW | 1-24h | ⚠️ A CRIAR |
| 20 | `maintenance_due` | Manutenção Vencida | 🟡 MEDIUM | 24h | ⚠️ A CRIAR |

#### Detalhamento dos Eventos Operacionais

**19. fuel_waste_detected** (Desperdício de Combustível)
- **Descrição:** Consumo real > consumo esperado
- **Detecção:** Cálculo baseado em distância + eventos
- **Fórmula:** `consumo_base + (harsh_accel * 5%) + (harsh_brake * 3%) + (speeding * 15%)`
- **Ação:** Sugestões de economia (smooth driving)
- **Dados:** `{consumption_real, consumption_expected, waste_percent, cost_monthly_BRL}`
- **Tempo resposta OK:** Análise diária, não precisa ser em tempo real

**20. maintenance_due** (Manutenção Vencida)
- **Descrição:** Km ou tempo de manutenção atingido
- **Tipos:** Troca de óleo, pneus, revisão
- **Detecção:** `km_atual >= km_previsto OR date >= date_prevista`
- **Ação:** Agendar manutenção preventiva
- **Dados:** `{maintenance_type, km_current, km_due, date_due}`
- **Requer:** Tabela `manutencoes`
- **Tempo resposta OK:** Pode avisar com dias/semanas de antecedência

---

## Arquitetura de Detecção

### ⚠️ IMPORTANTE: Diferença entre Event Agents e Monitors

**Este documento foca em EVENT AGENTS (detecção de eventos).**

Para a camada superior de **MONITORS AI** (análise de grupos de veículos com LLM), consulte:
📄 **[PLAN_AI_MONITORS.md](./PLAN_AI_MONITORS.md)** - Plano completo dos monitores AI

**Arquitetura completa:**
```
Event Agents (este documento) → Detectam eventos individuais
         ↓
Event Stream/Bus (este documento) → Redis Pub/Sub + MySQL
         ↓
Monitors AI (PLAN_AI_MONITORS.md) → Analisam padrões em grupos de veículos com LLM
         ↓
Alert Dispatcher → Gera alertas inteligentes
```

**Diferença:**
- **Event Agents:** Detectam eventos INDIVIDUAIS (harsh_brake, geofence_exit, etc.) baseado em regras/thresholds
- **Monitors AI:** Analisam PADRÕES em múltiplos eventos de múltiplos veículos usando LLM, geram insights e recomendações

**Exemplo:**
1. Event Agent detecta: `harsh_brake` às 10:30
2. Event Agent detecta: `harsh_brake` às 10:35
3. Event Agent detecta: `speeding` às 10:40
4. **Monitor AI** analisa: "8 harsh_brake em 30min + speeding = direção agressiva, recomendar coaching"

---

### Visão Geral em Camadas

```
┌────────────────────────────────────────────────────────────────┐
│                  CAMADA 1: INGESTÃO DE DADOS                   │
│  GPS Trackers → Socket Server (9000) → Protocol Parsers       │
│                              ↓                                 │
│                      MySQL (localizacao)                       │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│              CAMADA 2: DETECÇÃO DE EVENTOS                     │
│                     (Event Agents)                             │
│                                                                │
│  ┌──────────────────────────────────────────────────┐         │
│  │  Security Agents (A CRIAR)                       │         │
│  │  ├─ GeoFenceAgent      → geofence_exit/entry     │         │
│  │  ├─ PanicButtonAgent   → panic_button            │         │
│  │  ├─ TamperAgent        → tamper_detected         │         │
│  │  └─ TheftAgent         → theft_suspected         │         │
│  └──────────────────────────────────────────────────┘         │
│                                                                │
│  ┌──────────────────────────────────────────────────┐         │
│  │  Behavioral Agents (JÁ EXISTE)                   │         │
│  │  behavioral_engine.py ✅                          │         │
│  │  ├─ SpeedingAgent      → speeding                │         │
│  │  ├─ HarshBrakeAgent    → harsh_brake             │         │
│  │  ├─ HarshAccelAgent    → harsh_accel             │         │
│  │  └─ SharpTurnAgent     → sharp_turn              │         │
│  └──────────────────────────────────────────────────┘         │
│                                                                │
│  ┌──────────────────────────────────────────────────┐         │
│  │  Efficiency Agents (A CRIAR)                     │         │
│  │  ├─ IdleTimeAgent      → excessive_idle          │         │
│  │  ├─ FuelWasteAgent     → fuel_waste_detected     │         │
│  │  └─ RouteDeviationAgent→ route_deviation         │         │
│  └──────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│            CAMADA 3: EVENT STREAM/BUS (HÍBRIDO)                │
│                                                                │
│  ┌─────────────────────────────────────┐                      │
│  │  Redis Pub/Sub (Eventos Críticos)   │                      │
│  │  Canal: vehicle.critical_events     │                      │
│  │  - panic_button                      │                      │
│  │  - geofence_exit/entry               │                      │
│  │  - tamper_detected                   │                      │
│  │  - theft_suspected                   │                      │
│  │  - collision_detected                │                      │
│  │  Latência: <10ms                     │                      │
│  └─────────────────────────────────────┘                      │
│                                                                │
│  ┌─────────────────────────────────────┐                      │
│  │  MySQL Table: eventos                │                      │
│  │  (Behavioral + Operational)          │                      │
│  │  Polling interval: 60-300 segundos   │                      │
│  └─────────────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│          CAMADA 4: MONITORS (ANÁLISE COM LLM)                  │
│                                                                │
│  SecurityMonitor (escuta Redis)                                │
│  ├─ Analisa: panic, geofence, tamper, theft                   │
│  ├─ LLM: GPT-4-turbo                                           │
│  └─ Ação: Alerta CRÍTICO imediato                             │
│                                                                │
│  BehavioralMonitor (polling MySQL)                             │
│  ├─ Analisa: harsh_*, speeding, fatigue                       │
│  ├─ LLM: GPT-4-turbo ou GPT-3.5                               │
│  └─ Ação: Coaching, treinamento                               │
│                                                                │
│  EfficiencyMonitor (polling MySQL)                             │
│  ├─ Analisa: idle, fuel_waste, route_deviation                │
│  ├─ LLM: GPT-3.5-turbo (cheaper)                              │
│  └─ Ação: Recomendações de economia                           │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│              CAMADA 5: ALERT DISPATCHER                        │
│  - Prioriza por severidade (critical → low)                   │
│  - Roteia para: proprietário, gestor, motorista, polícia      │
│  - Persiste em: monitor_alertas                               │
│  - Notifica via: SMS, Push, Email, WebSocket                  │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│         CAMADA 6: APRESENTAÇÃO (FRONTEND)                      │
│  React App polling HTTP (a cada 3s) ← JÁ EXISTE               │
│  GET /api/posicoes, /api/fleet/events, /api/alerts            │
│  WebSocket (futuro): Alertas críticos push                    │
└────────────────────────────────────────────────────────────────┘
```

---

### Fluxo de Exemplo: Roubo de Veículo

```
02:34:00 AM
   ↓
[1] GeoFenceAgent detecta saída da cerca residencial
    └─> Publica no Redis: geofence_exit (severity: high)
   ↓
02:34:05 AM
   ↓
[2] TamperAgent detecta tentativa de desligar rastreador
    └─> Publica no Redis: main_power_cut (severity: critical)
   ↓
02:34:10 AM
   ↓
[3] TheftAgent correlaciona os 2 eventos
    └─> Publica no Redis: theft_suspected (confidence: 85%)
   ↓
02:34:10.050 AM (50ms depois)
   ↓
[4] SecurityMonitor recebe 3 eventos via Redis
    └─> LLM analisa contexto:
        {
          "events": [geofence_exit, main_power_cut, theft_suspected],
          "time": "02:34 AM",
          "location": "Zona residencial",
          "vehicle_history": "Sempre estacionado 22h-6h",
          "owner_phone": "+5511999999999"
        }
   ↓
02:34:15 AM (análise LLM completa)
   ↓
[5] LLM retorna:
    {
      "severity": "critical",
      "summary": "Alta probabilidade de roubo em andamento",
      "confidence": 92,
      "recommendations": [
        {"action": "Notificar proprietário IMEDIATAMENTE", "priority": "critical"},
        {"action": "Acionar polícia", "priority": "critical"},
        {"action": "Bloquear veículo remotamente", "priority": "high"}
      ]
    }
   ↓
02:34:16 AM
   ↓
[6] AlertDispatcher gera alerta CRÍTICO
    ├─> SMS para proprietário
    ├─> Push notification para app
    ├─> Email para gestor
    ├─> Webhook para polícia (se configurado)
    └─> Salva em monitor_alertas
   ↓
02:34:17 AM
   ↓
[7] Frontend recebe alerta via polling (próximo ciclo de 3s)
    └─> Exibe notificação crítica com som/vibração

Tempo total: 17 segundos (alerta → notificação)
```

**Sem Redis Pub/Sub (polling de 5min):**
- 02:34:00 - Evento acontece
- 02:39:00 - Monitor descobre (5 minutos depois) ❌
- Tempo total: **5 minutos e 17 segundos**

---

## Análise de Latência

### Cenário 1: Botão de Pânico

#### **Com MySQL Polling (intervalo 5 minutos)**
```
10:30:40 - Monitor consulta banco (nada)
10:35:40 - Monitor consulta banco (nada)
10:33:42 - [PÂNICO ACIONADO] ← Evento gravado no banco
          ↓
          ↓ Monitor dormindo...
          ↓
10:40:40 - Monitor consulta banco (DESCOBRE evento)
          ↓
10:40:45 - LLM analisa
10:40:46 - Alerta gerado

Latência total: 7 minutos e 4 segundos ❌
```

#### **Com Redis Pub/Sub**
```
10:33:42.000 - [PÂNICO ACIONADO]
10:33:42.005 - Agent publica no Redis
10:33:42.015 - Monitor recebe (10ms latência)
10:33:47.015 - LLM analisa (5s)
10:33:48.015 - Alerta gerado

Latência total: 6 segundos ✅
```

**Diferença:** 7min vs 6s = **70x mais rápido**

---

### Cenário 2: Direção Agressiva (Behavioral)

#### **Com MySQL Polling (intervalo 5 minutos)**
```
14:20:00 - Último check
14:22:30 - [8 harsh brakes em 10 minutos]
14:25:00 - Monitor descobre, LLM analisa
14:25:10 - Alerta gerado: "Direção agressiva, fazer coaching"

Latência: 2.5 minutos (aceitável) ✅
```

**Por quê é aceitável?** Não é emergência, análise de padrão pode aguardar minutos.

---

### Comparação Frontend Polling (Atual)

**Frontend: HTTP Polling a cada 3 segundos**
```typescript
useEffect(() => {
    const fetchData = async () => {
        const response = await axios.get('http://localhost:5009/api/posicoes');
        setVehicles(response.data);
    };

    fetchData();
    const intervalId = setInterval(fetchData, 3000);  // 3s
    return () => clearInterval(intervalId);
}, []);
```

**Latência:** 0-3 segundos para atualização visual
**Status:** ✅ Aceitável para UI (usuário não nota)
**Melhor abordagem:** WebSocket push (futuro)

---

## Schema do Banco de Dados

### Tabela: tipo_evento

Catálogo de todos os tipos de evento do sistema:

```sql
CREATE TABLE tipo_evento (
  id INT PRIMARY KEY AUTO_INCREMENT,
  codigo VARCHAR(50) UNIQUE NOT NULL COMMENT 'panic_button, harsh_brake, etc',
  nome VARCHAR(100) NOT NULL COMMENT 'Nome legível',
  categoria ENUM('critical', 'behavioral', 'operational') NOT NULL,
  severidade_padrao ENUM('low', 'medium', 'high', 'critical') NOT NULL,

  -- SLA e tecnologia
  tempo_resposta_segundos INT NOT NULL COMMENT 'SLA de resposta',
  requer_acao_imediata BOOLEAN DEFAULT FALSE,
  usa_redis BOOLEAN DEFAULT FALSE COMMENT 'TRUE=Pub/Sub, FALSE=MySQL Polling',

  -- Configuração
  descricao TEXT,
  icone VARCHAR(10) COMMENT 'Emoji para UI',
  cor_hex VARCHAR(7) COMMENT '#FF0000',

  -- Metadados
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  ativo BOOLEAN DEFAULT TRUE,

  INDEX idx_categoria (categoria),
  INDEX idx_usa_redis (usa_redis)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Inserir Tipos de Evento

```sql
-- Eventos Críticos
INSERT INTO tipo_evento (codigo, nome, categoria, severidade_padrao, tempo_resposta_segundos, requer_acao_imediata, usa_redis, icone, cor_hex) VALUES
('panic_button', 'Botão de Pânico', 'critical', 'critical', 10, TRUE, TRUE, '🆘', '#DC2626'),
('geofence_exit', 'Saída de Cerca', 'critical', 'critical', 30, TRUE, TRUE, '⚠️', '#EF4444'),
('geofence_entry', 'Entrada Área Proibida', 'critical', 'critical', 30, TRUE, TRUE, '🚫', '#B91C1C'),
('tamper_detected', 'Adulteração Rastreador', 'critical', 'critical', 15, TRUE, TRUE, '🔧', '#DC2626'),
('theft_suspected', 'Suspeita de Roubo', 'critical', 'critical', 30, TRUE, TRUE, '🚨', '#7F1D1D'),
('collision_detected', 'Colisão Detectada', 'critical', 'critical', 30, TRUE, TRUE, '💥', '#EF4444'),
('towing_detected', 'Reboque Não Autorizado', 'critical', 'high', 60, TRUE, TRUE, '🚛', '#F97316'),

-- Eventos Comportamentais
('harsh_brake', 'Frenagem Brusca', 'behavioral', 'medium', 300, FALSE, FALSE, '🛑', '#EF4444'),
('harsh_accel', 'Aceleração Brusca', 'behavioral', 'medium', 300, FALSE, FALSE, '⚡', '#F59E0B'),
('speeding', 'Excesso de Velocidade', 'behavioral', 'medium', 300, FALSE, FALSE, '🏎️', '#DC2626'),
('sharp_turn', 'Curva Fechada', 'behavioral', 'medium', 300, FALSE, FALSE, '↩️', '#F97316'),
('fatigue_suspected', 'Fadiga Detectada', 'behavioral', 'high', 600, FALSE, FALSE, '😴', '#F59E0B'),
('distracted_driving', 'Direção Distraída', 'behavioral', 'high', 600, FALSE, FALSE, '📱', '#F97316'),
('aggressive_driving', 'Direção Agressiva', 'behavioral', 'high', 1800, FALSE, FALSE, '😠', '#DC2626'),

-- Eventos Operacionais
('excessive_idle', 'Tempo Ocioso Excessivo', 'operational', 'low', 3600, FALSE, FALSE, '⏱️', '#10B981'),
('fuel_waste_detected', 'Desperdício Combustível', 'operational', 'low', 86400, FALSE, FALSE, '⛽', '#F59E0B'),
('route_deviation', 'Desvio de Rota', 'operational', 'medium', 900, FALSE, FALSE, '🗺️', '#F97316'),
('maintenance_due', 'Manutenção Vencida', 'operational', 'medium', 86400, FALSE, FALSE, '🔧', '#F59E0B'),
('low_battery', 'Bateria Fraca', 'operational', 'medium', 21600, FALSE, FALSE, '🔋', '#EF4444'),
('unusual_hours', 'Uso Fora de Horário', 'operational', 'medium', 1800, FALSE, FALSE, '🕐', '#F59E0B');
```

---

### Tabela: eventos

Armazena instâncias de eventos detectados:

```sql
CREATE TABLE eventos (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tipo_evento_id INT NOT NULL,

  -- Veículo
  veicod INT COMMENT 'Tracker vehicle',
  codusu_dirijabem INT COMMENT 'Dirijabem user',
  device_id VARCHAR(50) COMMENT 'Cached for quick lookup',

  -- Temporal
  timestamp DATETIME NOT NULL,
  processado BOOLEAN DEFAULT FALSE,
  processado_em DATETIME NULL,

  -- Espacial
  latitude DOUBLE,
  longitude DOUBLE,

  -- Contexto
  severidade ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  dados_adicionais JSON COMMENT 'Event-specific data',

  -- Relações
  evento_pai_id BIGINT NULL COMMENT 'For correlated events',

  FOREIGN KEY (tipo_evento_id) REFERENCES tipo_evento(id),
  FOREIGN KEY (evento_pai_id) REFERENCES eventos(id),

  INDEX idx_processado (processado, timestamp),
  INDEX idx_veicod (veicod),
  INDEX idx_tipo (tipo_evento_id),
  INDEX idx_severidade (severidade),
  INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Exemplo de dados_adicionais JSON:**

```json
// harsh_brake
{
  "speed_before": 80.5,
  "speed_after": 55.2,
  "deceleration_kmh_s": 25.3,
  "duration_seconds": 2.8
}

// panic_button
{
  "button_pressed": true,
  "speed_at_press": 45.0,
  "ignition_on": true
}

// geofence_exit
{
  "fence_id": 15,
  "fence_name": "Residência São Paulo",
  "distance_from_fence_meters": 150,
  "direction": "north"
}
```

---

### Tabela: cercas (Geofences)

```sql
CREATE TABLE cercas (
  id INT PRIMARY KEY AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  descricao TEXT,

  -- Geometria
  tipo ENUM('circular', 'polygon') NOT NULL,

  -- Circular
  centro_lat DOUBLE COMMENT 'For circular fences',
  centro_lon DOUBLE,
  raio_metros INT,

  -- Polygon
  coordenadas JSON COMMENT 'Array of {lat, lon} for polygon',

  -- Comportamento
  acao ENUM('alerta_entrada', 'alerta_saida', 'ambos') DEFAULT 'alerta_saida',
  severidade ENUM('low', 'medium', 'high', 'critical') DEFAULT 'high',
  tipo_area ENUM('safe', 'restricted', 'risk') DEFAULT 'safe',

  -- Estado
  ativo BOOLEAN DEFAULT TRUE,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_ativo (ativo)
) ENGINE=InnoDB;

-- Associação veículo-cerca
CREATE TABLE veiculo_cercas (
  id INT PRIMARY KEY AUTO_INCREMENT,
  veicod INT NOT NULL,
  cerca_id INT NOT NULL,
  ativo BOOLEAN DEFAULT TRUE,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (cerca_id) REFERENCES cercas(id),
  UNIQUE KEY uk_veiculo_cerca (veicod, cerca_id),
  INDEX idx_veicod (veicod)
) ENGINE=InnoDB;
```

---

## Roadmap de Implementação

### Fase 1: Behavioral Events (MySQL Polling) ✅ 40% Completo
**Duração:** 2 semanas
**Status:** 4/7 eventos implementados

- [x] harsh_brake (EXISTE em behavioral_engine.py)
- [x] harsh_accel (EXISTE)
- [x] speeding (EXISTE)
- [x] sharp_turn (EXISTE)
- [ ] fatigue_suspected (temporal analysis)
- [ ] distracted_driving (pattern analysis)
- [ ] aggressive_driving (fuzzy score trigger)

**Tarefas:**
1. Criar tabela `tipo_evento` e popular
2. Criar tabela `eventos`
3. Modificar behavioral_engine.py para gravar eventos na tabela
4. Implementar análise temporal para fadiga
5. Implementar análise de padrão para distração
6. Integrar fuzzy score com trigger de direção agressiva

---

### Fase 2: Security Agents + Redis Setup
**Duração:** 3 semanas
**Status:** 0% completo

**2.1 Infraestrutura Redis**
- [ ] Instalar Redis no servidor
- [ ] Configurar Redis como serviço (systemd)
- [ ] Criar biblioteca Python redis_client.py
- [ ] Implementar publish/subscribe patterns
- [ ] Testes de latência

**2.2 Security Agents**
- [ ] GeoFenceAgent
  - Criar tabelas `cercas` e `veiculo_cercas`
  - Implementar detecção circular e poligonal
  - Publicar eventos no Redis
- [ ] PanicButtonAgent
  - Parser de bit de pânico (Maxtrack, Suntech, Queclink)
  - Publicar no Redis
- [ ] TamperAgent
  - Detectar power_cut, antenna_cut, signal_loss, jamming
  - Correlação de sinais
  - Publicar no Redis
- [ ] TheftAgent
  - Correlação de múltiplos eventos
  - Machine learning de padrão (opcional)
  - Calcular confidence score
  - Publicar no Redis

**2.3 SecurityMonitor (AI)**
- [ ] Subscrever canal Redis
- [ ] Integração com LLM (GPT-4)
- [ ] Análise de contexto crítico
- [ ] Geração de alertas CRITICAL
- [ ] Notificações imediatas (SMS, Push)

---

### Fase 3: Operational Events
**Duração:** 2 semanas
**Status:** 0% completo

- [ ] IdleTimeAgent (excessive_idle)
- [ ] FuelWasteAgent (fuel_waste_detected)
- [ ] RouteDeviationAgent (route_deviation)
- [ ] MaintenanceAgent (maintenance_due)
- [ ] BatteryAgent (low_battery)
- [ ] UnusualHoursAgent (unusual_hours)

**Tarefas:**
1. Criar tabelas `rotas_planejadas`, `manutencoes`
2. Implementar cada agent
3. Gravar eventos na tabela `eventos`
4. EfficiencyMonitor com LLM (GPT-3.5 cheaper)

---

### Fase 4: Hybrid Architecture Integration
**Duração:** 1 semana
**Status:** 0% completo

- [ ] Refatorar monitors para suportar Redis + MySQL
- [ ] Load balancing de monitors
- [ ] Dashboards de latência
- [ ] Testes de carga
- [ ] Documentação final

---

## Status Atual do Sistema

### ✅ Implementado

**Frontend:**
- HTTP Polling a cada 3 segundos ✅
- Endpoints: `/api/posicoes`, `/api/fleet/scores`, `/api/fleet/events`
- Latência: 0-3s (aceitável para UI)

**Backend Behavioral:**
- `behavioral_engine.py` ✅
- 4 eventos detectados: harsh_brake, harsh_accel, speeding, sharp_turn
- Scores in-memory
- Thresholds configuráveis

**Fuzzy Logic:**
- `driverprofile.fcl` ✅
- 12 input variables (OST, OSA, OSP, SAM, SAA, etc.)
- 21 fuzzy rules
- Output: PERFIL (NORMAL/MODERADO/AGRESSIVO)
- Documentado em `driverprofile.md`

---

### ⚠️ Não Implementado

**Eventos Críticos:** 0/7
- panic_button
- geofence_exit/entry
- tamper_detected
- theft_suspected
- collision_detected
- towing_detected

**Eventos Comportamentais:** 3/7
- fatigue_suspected
- distracted_driving
- aggressive_driving

**Eventos Operacionais:** 0/6
- Todos (excessive_idle, fuel_waste, route_deviation, maintenance_due, low_battery, unusual_hours)

**Infraestrutura:**
- Redis Pub/Sub ❌
- Tabela `tipo_evento` ❌
- Tabela `eventos` ❌
- Tabela `cercas` ❌
- Security Agents ❌
- Monitors AI ❌

---

### 📊 Progresso Geral

| Categoria | Completo | Total | % |
|-----------|----------|-------|---|
| Eventos Críticos | 0 | 7 | 0% |
| Eventos Comportamentais | 4 | 7 | 57% |
| Eventos Operacionais | 0 | 6 | 0% |
| **TOTAL** | **4** | **20** | **20%** |

**Infraestrutura:**
- Database schema: 0%
- Redis setup: 0%
- Security agents: 0%
- Monitors AI: 0%
- Frontend UI: 0%

---

## Recomendações

### 1. Prioridade Imediata: Security Events
**Por quê:** Eventos críticos têm maior ROI (prevenir roubo = economizar R$50k+)

**Ação:**
1. Instalar Redis (1 dia)
2. Implementar GeoFenceAgent (3 dias)
3. Implementar PanicButtonAgent (2 dias)
4. SecurityMonitor básico sem LLM (2 dias)

**Resultado:** Sistema funcional de segurança em 1-2 semanas

---

### 2. Quick Win: Finalizar Behavioral Events
**Por quê:** 4/7 já existem, falta pouco

**Ação:**
1. Criar tabelas `tipo_evento` e `eventos` (1 dia)
2. Modificar behavioral_engine.py para gravar (1 dia)
3. Implementar fatigue + distraction detection (3 dias)

**Resultado:** Sistema behavioral completo em 1 semana

---

### 3. Arquitetura Híbrida desde o Início
**Por quê:** Evita refatoração futura

**Decisão:**
- **Redis Pub/Sub:** eventos critical (7 eventos)
- **MySQL Polling:** eventos behavioral + operational (13 eventos)

**Benefício:** Latência ótima onde importa + simplicidade onde é suficiente

---

### 4. Teste com Dados Reais
**Por quê:** Validar thresholds e reduzir falsos positivos

**Ação:**
1. Rodar sistema em produção com 10 veículos piloto
2. Coletar métricas de falsos positivos/negativos
3. Ajustar thresholds (HARSH_BRAKE_THRESHOLD, etc.)
4. Refinar prompts LLM

---

## Integração com Monitors AI

Este documento define a **camada de detecção de eventos** (Event Agents).

Para a **camada de análise inteligente** (Monitors AI), consulte:

📄 **[PLAN_AI_MONITORS.md](./PLAN_AI_MONITORS.md)** que contém:

**Database Schema (4 tabelas):**
- `monitores` - Configuração dos monitores AI (nome, tipo, prompt LLM, intervalo)
- `veiculomonitor` - Associação veículo-monitor (qual monitor vigia quais veículos)
- `monitor_analises` - Análises geradas pelo LLM (conclusões, padrões, recomendações)
- `monitor_alertas` - Alertas inteligentes baseados nas análises

**Monitor Engine:**
- APScheduler rodando monitores em intervalos configuráveis (5min, 15min, etc.)
- LLM integration (OpenAI GPT-4, Anthropic Claude)
- Rate limiting (20 RPM)
- Cost controls ($9/mês estimado)

**Exemplos de Monitores:**
- Aggressive Driving Detector - Analisa harsh_brake + speeding + sharp_turn
- Fatigue Detector - Detecta aumento de taxa de eventos ao longo do tempo
- Efficiency Coach - Analisa desperdício de combustível

**Fluxo Completo:**
```
1. Event Agent detecta evento → Publica no Event Stream
2. Monitor AI consome eventos → Analisa padrão com LLM
3. LLM retorna insights → Monitor gera alerta
4. Alert Dispatcher → Notifica gestor/motorista
```

**Interface Web:**
- MonitorDashboard.tsx - Criar/editar monitores, alocar veículos
- AlertsPanel.tsx - Visualizar e reconhecer alertas

---

## Conclusão

Este documento define a **camada de detecção de eventos** do sistema de monitoramento AITrack DataDrivr:

- **20 tipos de evento** classificados por criticidade
- **Arquitetura híbrida** (Redis + MySQL) otimizada para latência vs complexidade
- **8 eventos críticos** requerem resposta <30s (Redis Pub/Sub)
- **12 eventos não-críticos** podem usar polling MySQL
- **4/20 eventos já implementados** (behavioral_engine.py)
- **Roadmap claro** com 4 fases e estimativas

**Camada superior (Monitors AI):** Ver [PLAN_AI_MONITORS.md](./PLAN_AI_MONITORS.md) para:
- Database schema dos monitores (4 tabelas)
- Monitor Engine com LLM integration
- Exemplos de prompts e análises
- Interface de alocação de veículos
- Estimativa de custos ($9/mês)

**Próximo passo:**
1. Implementar Event Agents (este documento) - Fase 1 behavioral ou Fase 2 security
2. Implementar Monitors AI (PLAN_AI_MONITORS.md) - 21 horas estimadas

---

**Versão:** 1.0
**Data:** 2026-02-10
**Autores:** AITrack Team + Claude Sonnet 4.5
**Repositório:** `/home/pasteurjr/progreact/aitrack/aitrackdatadrivr/`
