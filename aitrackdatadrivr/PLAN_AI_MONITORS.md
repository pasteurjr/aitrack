# Plan: AI Monitor Agents System for AITrack DataDrivr

## Context

Adding intelligent monitoring agents to the existing AITrack DataDrivr platform. Monitors are AI agents (using LLMs) that continuously watch groups of vehicles for behavioral patterns, generate insights, and create alerts.

**Existing System:**
- MySQL database `tracker` with tables: `veiculos`, `localizacao`
- Separate `dirijabem` database with `viagem`, `localizacaodados`
- Behavioral engine detecting events: harsh_accel, harsh_brake, speeding, sharp_turn
- Events stored in-memory with scores (starting at 85.0)
- Frontend polls API every 3 seconds

**New Requirements:**
1. Table `monitores` - AI agents with configurable behavior
2. Table `veiculomonitor` - Associates vehicles (tracker OR dirijabem) with monitors
3. Continuous monitoring system using LLM for analysis
4. Alert generation with recommendations

## Database Schema

### Table: monitores

```sql
CREATE TABLE monitores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(100) NOT NULL COMMENT 'Monitor name (e.g., "Aggressive Driving Detector")',
  descricao TEXT COMMENT 'Description of monitor purpose',
  tipo_monitor ENUM('safety', 'efficiency', 'compliance', 'predictive', 'custom') NOT NULL DEFAULT 'safety',

  -- AI/LLM Configuration
  prompt_template TEXT NOT NULL COMMENT 'LLM prompt with {placeholders}',
  modelo_llm VARCHAR(50) DEFAULT 'gpt-4-turbo' COMMENT 'LLM model (gpt-4, claude-3, etc.)',
  temperatura FLOAT DEFAULT 0.3 COMMENT 'LLM temperature (0.0-1.0)',
  max_tokens INT DEFAULT 500 COMMENT 'Maximum response tokens',

  -- Monitoring Behavior
  intervalo_analise INT DEFAULT 300 COMMENT 'Analysis interval in seconds (default: 5 min)',
  janela_contexto INT DEFAULT 1800 COMMENT 'Context window in seconds (default: 30 min)',
  eventos_minimos INT DEFAULT 3 COMMENT 'Minimum events to trigger analysis',
  score_threshold FLOAT DEFAULT 70.0 COMMENT 'Only analyze vehicles below this score',

  -- Alert Configuration
  gera_alertas BOOLEAN DEFAULT TRUE COMMENT 'Whether to generate alerts',
  severidade_minima ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
  notificar_gestor BOOLEAN DEFAULT FALSE COMMENT 'Send alerts to fleet manager',
  notificar_motorista BOOLEAN DEFAULT FALSE COMMENT 'Send alerts to driver',

  -- State
  ativo BOOLEAN DEFAULT TRUE COMMENT 'Monitor is active',
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_ativo (ativo),
  INDEX idx_tipo (tipo_monitor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Table: veiculomonitor

Uses **separate columns approach** for referencing both tracker vehicles and dirijabem users:

```sql
CREATE TABLE veiculomonitor (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL COMMENT 'Reference to monitores table',

  -- Vehicle Reference (either tracker OR dirijabem)
  tipo_veiculo ENUM('tracker', 'dirijabem') NOT NULL COMMENT 'Which system this vehicle comes from',
  veicod_tracker INT NULL COMMENT 'FK to tracker.veiculos.VEICOD (for tracker vehicles)',
  codusu_dirijabem INT NULL COMMENT 'FK to dirijabem users (for dirijabem users)',

  -- Metadata
  device_id VARCHAR(50) NULL COMMENT 'Cached device_id for quick lookup',
  notas TEXT COMMENT 'Admin notes about this assignment',
  atribuido_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  ativo BOOLEAN DEFAULT TRUE,

  -- Constraints
  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,

  -- Validation: exactly one of veicod_tracker or codusu_dirijabem must be set
  CONSTRAINT chk_vehicle_reference CHECK (
    (tipo_veiculo = 'tracker' AND veicod_tracker IS NOT NULL AND codusu_dirijabem IS NULL) OR
    (tipo_veiculo = 'dirijabem' AND codusu_dirijabem IS NOT NULL AND veicod_tracker IS NULL)
  ),

  -- Prevent duplicate assignments
  UNIQUE KEY uk_monitor_tracker (monitor_id, veicod_tracker),
  UNIQUE KEY uk_monitor_dirijabem (monitor_id, codusu_dirijabem),

  INDEX idx_monitor (monitor_id),
  INDEX idx_tipo (tipo_veiculo),
  INDEX idx_device (device_id),
  INDEX idx_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Table: monitor_analises

Stores AI analysis results:

```sql
CREATE TABLE monitor_analises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL COMMENT 'Which vehicle assignment triggered this',

  -- Analysis Context
  analisado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  periodo_inicio DATETIME NOT NULL COMMENT 'Start of analysis window',
  periodo_fim DATETIME NOT NULL COMMENT 'End of analysis window',

  -- Input Context
  eventos_analisados JSON COMMENT 'Array of event timestamps',
  score_inicial FLOAT COMMENT 'Vehicle score at period start',
  score_final FLOAT COMMENT 'Vehicle score at period end',
  contexto_prompt TEXT COMMENT 'Full prompt sent to LLM',

  -- LLM Response
  resposta_llm TEXT COMMENT 'Raw LLM response',
  modelo_usado VARCHAR(50) COMMENT 'LLM model used',
  tokens_usados INT COMMENT 'Total tokens consumed',
  tempo_resposta_ms INT COMMENT 'Response time in milliseconds',

  -- Structured Output (parsed from LLM)
  conclusao TEXT COMMENT 'Main conclusion/summary',
  severidade ENUM('low', 'medium', 'high', 'critical') COMMENT 'Assessed severity',
  padroes_identificados JSON COMMENT 'Array of behavior patterns found',
  recomendacoes JSON COMMENT 'Array of recommended actions',
  metricas JSON COMMENT 'Calculated metrics',

  -- Actions Taken
  alerta_gerado BOOLEAN DEFAULT FALSE,
  alerta_id INT NULL COMMENT 'Reference to monitor_alertas if alert created',

  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,
  FOREIGN KEY (veiculomonitor_id) REFERENCES veiculomonitor(id) ON DELETE CASCADE,

  INDEX idx_monitor_data (monitor_id, analisado_em),
  INDEX idx_veiculo (veiculomonitor_id),
  INDEX idx_severidade (severidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Table: monitor_alertas

Stores generated alerts:

```sql
CREATE TABLE monitor_alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  analise_id INT NOT NULL COMMENT 'Reference to monitor_analises',
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL,

  -- Alert Content
  titulo VARCHAR(200) NOT NULL COMMENT 'Alert title/summary',
  mensagem TEXT NOT NULL COMMENT 'Full alert message',
  severidade ENUM('low', 'medium', 'high', 'critical') NOT NULL,
  tipo ENUM('behavior', 'safety', 'efficiency', 'compliance', 'prediction') DEFAULT 'behavior',

  -- Context
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  eventos_relacionados JSON COMMENT 'Array of event timestamps',
  localizacao_lat DOUBLE NULL COMMENT 'Location of most critical event',
  localizacao_lon DOUBLE NULL COMMENT 'Location of most critical event',

  -- Status
  status ENUM('pending', 'acknowledged', 'resolved', 'dismissed') DEFAULT 'pending',
  reconhecido_em DATETIME NULL,
  reconhecido_por VARCHAR(100) NULL,
  resolvido_em DATETIME NULL,
  notas_resolucao TEXT,

  FOREIGN KEY (analise_id) REFERENCES monitor_analises(id) ON DELETE CASCADE,
  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE,
  FOREIGN KEY (veiculomonitor_id) REFERENCES veiculomonitor(id) ON DELETE CASCADE,

  INDEX idx_monitor (monitor_id),
  INDEX idx_status (status),
  INDEX idx_severidade (severidade),
  INDEX idx_criado (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   AITrack System                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────┐        ┌────────────┐                 │
│  │Socket      │        │Flask API   │                 │
│  │Server 9000 │        │Port 5000   │                 │
│  └─────┬──────┘        └─────┬──────┘                 │
│        │                     │                         │
│        ▼                     ▼                         │
│  ┌──────────────────────────────────┐                 │
│  │  Behavioral Engine (In-Memory)   │                 │
│  │  - vehicle_events[]              │                 │
│  │  - vehicle_scores{}              │                 │
│  └───────────┬──────────────────────┘                 │
│              │                                         │
│              ▼                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │       Monitor Engine (Separate Process)          │ │
│  │                                                   │ │
│  │  ┌──────────────────────────────────┐           │ │
│  │  │ APScheduler                      │           │ │
│  │  │ - Runs monitors every N seconds  │           │ │
│  │  └─────────┬────────────────────────┘           │ │
│  │            │                                     │ │
│  │            ▼                                     │ │
│  │  ┌──────────────────────────────────┐           │ │
│  │  │ Monitor Workers                  │           │ │
│  │  │ - Monitor 1: Aggressive Driving  │           │ │
│  │  │ - Monitor 2: Fatigue Detection   │           │ │
│  │  │ - Monitor 3: Efficiency Coach    │           │ │
│  │  └─────────┬────────────────────────┘           │ │
│  │            │                                     │ │
│  │            ▼                                     │ │
│  │  ┌──────────────────────────────────┐           │ │
│  │  │ Context Builder                  │           │ │
│  │  │ - Gets events from engine        │           │ │
│  │  │ - Aggregates statistics          │           │ │
│  │  │ - Formats prompt                 │           │ │
│  │  └─────────┬────────────────────────┘           │ │
│  │            │                                     │ │
│  │            ▼                                     │ │
│  │  ┌──────────────────────────────────┐           │ │
│  │  │ LLM Client (OpenAI/Anthropic)    │           │ │
│  │  │ - Rate limiter (20 RPM)          │           │ │
│  │  │ - Retry logic                    │           │ │
│  │  │ - Token tracking                 │           │ │
│  │  └─────────┬────────────────────────┘           │ │
│  │            │                                     │ │
│  │            ▼                                     │ │
│  │  ┌──────────────────────────────────┐           │ │
│  │  │ Alert Generator                  │           │ │
│  │  │ - Saves to MySQL                 │           │ │
│  │  │ - Sends notifications            │           │ │
│  │  └──────────────────────────────────┘           │ │
│  └──────────────────────────────────────────────────┘ │
│                     │                                  │
│                     ▼                                  │
│  ┌──────────────────────────────────┐                 │
│  │    MySQL Database                │                 │
│  │  - monitores                     │                 │
│  │  - veiculomonitor                │                 │
│  │  - monitor_analises              │                 │
│  │  - monitor_alertas               │                 │
│  └──────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### Monitor Engine Process

Separate Python process that runs continuously:
- **Scheduler:** APScheduler runs each monitor at configured intervals (default: 5 min)
- **Workers:** ThreadPoolExecutor (10 workers) for parallel vehicle analysis
- **LLM Integration:** Calls OpenAI/Anthropic with rate limiting
- **Persistence:** Saves analyses and alerts to MySQL

**Startup:**
```bash
# Start main system
python run.py

# Start monitor engine (separate terminal)
python -m server.monitor_engine
```

## Example Monitor Prompts

### 1. Aggressive Driving Detector

**Prompt Template:**
```
You are analyzing driver behavior for vehicle {vehicle[device_id]} (Score: {vehicle[score_atual]}/100).

TIME: Last {periodo[janela_minutos]} minutes

EVENTS:
- Total: {estatisticas[total_eventos]}
- Harsh Braking: {estatisticas[eventos_por_tipo].get('harsh_brake', 0)}
- Harsh Acceleration: {estatisticas[eventos_por_tipo].get('harsh_accel', 0)}
- Speeding: {estatisticas[eventos_por_tipo].get('speeding', 0)}

SEVERITY:
- Critical: {estatisticas[eventos_por_severidade].get('critical', 0)}
- High: {estatisticas[eventos_por_severidade].get('high', 0)}

MOST CRITICAL:
{evento_mais_critico[type]} at {evento_mais_critico[timestamp]}
Speed: {evento_mais_critico.get('speed', 'N/A')} km/h

TASK: Assess behavior pattern, identify risks, provide 2-3 recommendations.

Respond in JSON:
{{
  "summary": "Brief conclusion (max 200 chars)",
  "severity": "low|medium|high|critical",
  "patterns": ["Pattern 1", "Pattern 2"],
  "recommendations": [
    {{"action": "Description", "priority": "high|medium|low"}}
  ],
  "metrics": {{"risk_score": 0-100}}
}}
```

**Expected Output:**
```json
{
  "summary": "Aggressive driving: 12 events in 30 min, score 62.3",
  "severity": "high",
  "patterns": [
    "Frequent harsh braking indicates poor anticipation",
    "Speeding violations correlate with hard brakes"
  ],
  "recommendations": [
    {"action": "Maintain 3-second following distance", "priority": "high"},
    {"action": "Reduce cruising speed to 70 km/h", "priority": "high"}
  ],
  "metrics": {"risk_score": 82}
}
```

### 2. Fatigue Detector

**Prompt Template:**
```
Analyzing fatigue for vehicle {vehicle[device_id]}.

CONTEXT:
- Window: {periodo[janela_minutos]} minutes
- Total Events: {estatisticas[total_eventos]}
- Pattern: {estatisticas[distribuicao_temporal]}

RECENT EVENTS: {eventos_recentes}

TASK: Detect fatigue signs (increasing events, micro-corrections).

Respond in JSON with fatigue_score (0-100) and rest_recommended (bool).
```

**Expected Output:**
```json
{
  "summary": "Fatigue detected: Event rate doubled over 90 minutes",
  "severity": "medium",
  "patterns": [
    "Event rate increasing: 4 → 6 → 8 per 30-min period",
    "Multiple low-severity turns suggest lane drift"
  ],
  "recommendations": [
    {"action": "Take 15-minute rest break", "priority": "high"}
  ],
  "metrics": {"fatigue_score": 68, "rest_recommended": true}
}
```

### 3. Efficiency Coach

**Prompt Template:**
```
Analyzing fuel efficiency for {vehicle[device_id]}.

EFFICIENCY METRICS:
- Harsh Accelerations: {estatisticas[eventos_por_tipo].get('harsh_accel', 0)} (+5% fuel each)
- Harsh Braking: {estatisticas[eventos_por_tipo].get('harsh_brake', 0)} (+3% fuel each)
- Speeding: {estatisticas[eventos_por_tipo].get('speeding', 0)} (+10-20% fuel)

TASK: Calculate fuel waste, provide eco-driving tips.

Respond in JSON with estimated_fuel_waste_percent and potential_savings_monthly.
```

**Expected Output:**
```json
{
  "summary": "Fuel waste: 4 harsh accelerations = 20% extra consumption",
  "severity": "low",
  "patterns": ["Jack-rabbit starts", "Not using engine braking"],
  "recommendations": [
    {"action": "Accelerate gradually (0-60 in 15s)", "priority": "medium"}
  ],
  "metrics": {
    "estimated_fuel_waste_percent": 18,
    "potential_savings_monthly": "R$ 250"
  }
}
```

## Implementation Files

### New Files to Create

1. **server/monitor_engine.py** (NEW)
   - Core monitor scheduler
   - LLM client integration
   - Alert generator
   - Classes:
     - `MonitorEngine` - Main orchestrator
     - `LLMClient` - OpenAI/Anthropic wrapper
     - `ContextBuilder` - Prepares LLM prompts
     - `AlertGenerator` - Creates alerts in DB

2. **server/monitor_api.py** (NEW)
   - REST API endpoints for monitors
   - Routes:
     - `POST /api/monitors` - Create monitor
     - `GET /api/monitors` - List monitors
     - `PUT /api/monitors/{id}` - Update monitor
     - `POST /api/monitors/{id}/vehicles` - Assign vehicles
     - `GET /api/monitors/{id}/analyses` - Get analysis history
     - `GET /api/alerts` - List alerts
     - `PUT /api/alerts/{id}/acknowledge` - Acknowledge alert

3. **server/monitor_db.py** (NEW)
   - Database operations for monitor tables
   - Functions:
     - `get_active_monitors()`
     - `get_monitor_vehicles(monitor_id)`
     - `save_analysis(monitor_id, vehicle_id, llm_response)`
     - `create_alert(analysis_id, severity, message)`

4. **frontend/src/components/MonitorDashboard.tsx** (NEW)
   - UI for monitor management
   - Features:
     - List active monitors
     - Create/edit monitors
     - Assign vehicles to monitors
     - View analysis history

5. **frontend/src/components/AlertsPanel.tsx** (NEW)
   - UI for viewing alerts
   - Features:
     - Real-time alert list
     - Filter by severity/status
     - Acknowledge/resolve alerts
     - View recommendations

### Files to Modify

1. **server/api.py**
   - Import and register monitor_api blueprint
   - Add CORS for new endpoints

2. **server/behavioral_engine.py**
   - Export `get_recent_events()` function (already exists)
   - Export `get_vehicle_score()` function (already exists)

3. **frontend/src/App.tsx**
   - Add routes for MonitorDashboard and AlertsPanel
   - Add sidebar links

## Configuration

### Environment Variables

Add to `.env` or `config/.env`:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Monitor Settings
MONITOR_DEFAULT_INTERVAL=300  # seconds
MONITOR_MAX_WORKERS=10
MONITOR_RATE_LIMIT_RPM=20

# Cost Control
MONITOR_DAILY_BUDGET_USD=50
MONITOR_MIN_EVENTS=3
MONITOR_SCORE_THRESHOLD=70
```

### Default Monitors

Create 3 default monitors on first startup:

```python
DEFAULT_MONITORS = [
    {
        "nome": "Aggressive Driving Detector",
        "tipo_monitor": "safety",
        "prompt_template": AGGRESSIVE_DRIVING_PROMPT,
        "intervalo_analise": 300,  # 5 minutes
        "janela_contexto": 1800,   # 30 minutes
        "eventos_minimos": 3,
        "score_threshold": 70.0
    },
    {
        "nome": "Fatigue Detector",
        "tipo_monitor": "safety",
        "prompt_template": FATIGUE_MONITOR_PROMPT,
        "intervalo_analise": 900,  # 15 minutes
        "janela_contexto": 5400,   # 90 minutes
        "eventos_minimos": 5,
        "score_threshold": 75.0
    },
    {
        "nome": "Efficiency Coach",
        "tipo_monitor": "efficiency",
        "prompt_template": EFFICIENCY_MONITOR_PROMPT,
        "intervalo_analise": 600,  # 10 minutes
        "janela_contexto": 3600,   # 60 minutes
        "eventos_minimos": 3,
        "score_threshold": 80.0
    }
]
```

## Cost Management

### Estimated Costs

**Assumptions:**
- 50 vehicles in fleet
- 10% of vehicles trigger analysis daily (score < 70)
- 5 vehicles × 12 analyses/day = 60 analyses/day
- GPT-4-turbo: $0.01 per 1K tokens, ~500 tokens per analysis = $0.005/analysis
- Daily cost: $0.30/day = **$9/month**

**Budget Controls:**
1. Score threshold: Only analyze vehicles with score < 70
2. Min events: Require at least 3 events before analysis
3. Rate limiting: Max 20 API calls/minute
4. Daily budget: Stop all monitors if cost > $50/day

### Optimization Strategies

1. **Use cheaper models for low-priority:**
   - GPT-3.5-turbo for efficiency coach ($0.0005/analysis)
   - GPT-4-turbo for safety monitors ($0.005/analysis)

2. **Batch processing:**
   - Analyze multiple vehicles in single prompt (reduces overhead)

3. **Caching:**
   - Cache similar contexts to avoid duplicate LLM calls

## Verification Tests

### Test 1: Database Schema
```bash
# Create tables
mysql -h camerascasas.no-ip.info -P 3307 -u scadabr -p tracker < schema.sql

# Verify tables exist
mysql> SHOW TABLES LIKE 'monitor%';
+---------------------------+
| Tables_in_tracker         |
+---------------------------+
| monitor_alertas           |
| monitor_analises          |
| monitores                 |
| veiculomonitor            |
+---------------------------+
```

### Test 2: Monitor Engine Startup
```bash
# Start monitor engine
python -m server.monitor_engine

# Expected output:
[INFO] Starting Monitor Engine...
[INFO] Scheduled monitor Aggressive Driving Detector (interval: 300s)
[INFO] Scheduled monitor Fatigue Detector (interval: 900s)
[INFO] Monitor Engine started successfully
```

### Test 3: Create Monitor via API
```bash
curl -X POST http://localhost:5000/api/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Test Monitor",
    "tipo_monitor": "safety",
    "prompt_template": "Analyze vehicle {vehicle[device_id]}",
    "intervalo_analise": 300
  }'

# Expected: {"id": 1, "status": "created"}
```

### Test 4: Assign Vehicle to Monitor
```bash
curl -X POST http://localhost:5000/api/monitors/1/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_veiculo": "tracker",
    "veicod_tracker": 123,
    "device_id": "SIM-1005"
  }'

# Expected: {"veiculomonitor_id": 1, "status": "assigned"}
```

### Test 5: Trigger Analysis
```bash
# Wait for monitor interval, or trigger manually:
curl -X POST http://localhost:5000/api/monitors/1/run-now

# Check analysis in database:
mysql> SELECT * FROM monitor_analises ORDER BY analisado_em DESC LIMIT 1;

# Expected: 1 row with LLM response and parsed JSON
```

### Test 6: Verify Alert Generation
```bash
# Simulate vehicle with low score and high events
# Monitor should generate alert automatically

curl http://localhost:5000/api/alerts

# Expected: JSON array with alerts
[
  {
    "id": 1,
    "titulo": "Aggressive driving detected",
    "severidade": "high",
    "status": "pending",
    "criado_em": "2026-01-28T15:30:00"
  }
]
```

### Test 7: Frontend Integration
1. Navigate to http://localhost:3000/monitors
2. Verify monitor list displays 3 default monitors
3. Click "Assign Vehicles" button
4. Select vehicle from dropdown
5. Verify assignment saved
6. Navigate to Alerts panel
7. Verify alerts appear with acknowledge/resolve buttons

## Implementation Order

1. **Database Schema** (1h)
   - Create 4 new tables in MySQL
   - Add indexes
   - Test constraints

2. **Monitor DB Layer** (2h)
   - Create `server/monitor_db.py`
   - Implement CRUD functions
   - Test with sample data

3. **Monitor Engine Core** (4h)
   - Create `server/monitor_engine.py`
   - Implement scheduler
   - Add LLM client wrapper
   - Test with mock LLM responses

4. **Monitor API** (3h)
   - Create `server/monitor_api.py`
   - Implement all endpoints
   - Test with curl/Postman

5. **LLM Integration** (3h)
   - Add OpenAI client
   - Implement rate limiting
   - Add retry logic
   - Test with real API key

6. **Alert System** (2h)
   - Implement alert generation
   - Add notification stubs (email/webhook)
   - Test alert workflow

7. **Frontend UI** (4h)
   - Create MonitorDashboard component
   - Create AlertsPanel component
   - Add to App.tsx routing
   - Test full user flow

8. **Integration Testing** (2h)
   - End-to-end test
   - Performance testing
   - Cost tracking validation

**Total Estimated Time:** 21 hours

## Success Criteria

✅ All 4 database tables created successfully
✅ Monitor engine starts and schedules monitors
✅ LLM API calls succeed with rate limiting
✅ Analyses saved to database with structured JSON
✅ Alerts generated when severity threshold met
✅ Frontend displays monitors and alerts
✅ Vehicle assignment works for both tracker and dirijabem
✅ Daily budget controls prevent cost overruns
✅ System runs continuously for 24h without crashes

## Risk Mitigation

**Risk 1: LLM API failures**
- Mitigation: Retry logic (3 attempts with exponential backoff)
- Fallback: Rule-based analysis if LLM unavailable

**Risk 2: High costs**
- Mitigation: Daily budget hard limit ($50)
- Monitoring: Track tokens per analysis, alert if exceeds baseline

**Risk 3: Monitor failures**
- Mitigation: Log errors, continue to next vehicle
- Recovery: Auto-restart monitor engine on crash (systemd/supervisor)

**Risk 4: Database connection issues**
- Mitigation: Connection pool with auto-reconnect
- Backup: Queue analyses in memory, flush when DB recovers
