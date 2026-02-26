# PLANO V2: Roadmap Mock → Implementação Real
## Sistema de Monitores AI com LLM

**Data:** 10 de Fevereiro de 2026
**Versão Atual:** Mock Data para Demonstração
**Objetivo:** Transformar interfaces mock em sistema funcional com AI/LLM

---

## Status Atual (Mock v1.0)

### ✅ Implementado

1. **Frontend Completo com Mock Data**
   - `MonitorDashboard.tsx` - Interface de gerenciamento de monitores
   - `AlertsPanel.tsx` - Painel de alertas com filtros e detalhes
   - `EventsCatalog.tsx` - Catálogo completo de 20 tipos de eventos
   - Integração com `App.tsx` - 6 tabs de navegação
   - Dados mock realistas em português

2. **Estrutura de Dados Mock**
   - `mockMonitors.ts` - 5 monitores configurados
   - `mockAlerts.ts` - 8 alertas detalhados com análises LLM
   - `mockEvents.ts` - 20+ eventos recentes de 3 categorias
   - Estatísticas agregadas

3. **Conceitos Demonstrados**
   - Monitor monitora GRUPO de veículos (não eventos específicos)
   - Monitor vê TODOS os eventos (críticos + comportamentais + operacionais)
   - LLM analisa TODOS os eventos para identificar padrões
   - Propósito do monitor define FOCO da análise (não filtra eventos)

4. **Documentação**
   - `MONITORAMENTO_EVENTOS.md` - Arquitetura de eventos (20 tipos, polling vs pub/sub)
   - `PLAN_AI_MONITORS.md` - Schema de banco de dados e arquitetura LLM
   - `driverprofile.md` - Sistema fuzzy logic (12 métricas, 21 regras)

---

## Fase 1: Backend - Database & API (2-3 semanas)

### 1.1 Schema de Banco de Dados (3 dias)

**Criar 4 tabelas no MySQL:**

```sql
-- Tabela principal de monitores
CREATE TABLE monitores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  descricao TEXT,
  tipo_monitor ENUM('safety', 'efficiency', 'compliance', 'predictive', 'custom'),
  prompt_template TEXT NOT NULL,
  modelo_llm VARCHAR(50) DEFAULT 'gpt-4-turbo',
  temperatura FLOAT DEFAULT 0.3,
  intervalo_analise INT DEFAULT 300,
  janela_contexto INT DEFAULT 1800,
  eventos_minimos INT DEFAULT 3,
  score_threshold FLOAT DEFAULT 70.0,
  gera_alertas BOOLEAN DEFAULT TRUE,
  ativo BOOLEAN DEFAULT TRUE,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Associação veículo-monitor (suporta tracker E dirijabem)
CREATE TABLE veiculomonitor (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL,
  tipo_veiculo ENUM('tracker', 'dirijabem'),
  veicod_tracker INT NULL,
  codusu_dirijabem INT NULL,
  device_id VARCHAR(50),
  ativo BOOLEAN DEFAULT TRUE,
  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE
);

-- Análises geradas pela LLM
CREATE TABLE monitor_analises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL,
  analisado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  periodo_inicio DATETIME,
  periodo_fim DATETIME,
  eventos_analisados JSON,
  score_inicial FLOAT,
  score_final FLOAT,
  resposta_llm TEXT,
  modelo_usado VARCHAR(50),
  tokens_usados INT,
  conclusao TEXT,
  severidade ENUM('low', 'medium', 'high', 'critical'),
  padroes_identificados JSON,
  recomendacoes JSON,
  FOREIGN KEY (monitor_id) REFERENCES monitores(id) ON DELETE CASCADE
);

-- Alertas gerados
CREATE TABLE monitor_alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  analise_id INT NOT NULL,
  monitor_id INT NOT NULL,
  veiculomonitor_id INT NOT NULL,
  titulo VARCHAR(200),
  mensagem TEXT,
  severidade ENUM('low', 'medium', 'high', 'critical'),
  tipo ENUM('behavior', 'safety', 'efficiency', 'compliance', 'prediction'),
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('pending', 'acknowledged', 'resolved', 'dismissed') DEFAULT 'pending',
  eventos_relacionados JSON,
  FOREIGN KEY (analise_id) REFERENCES monitor_analises(id) ON DELETE CASCADE
);
```

**Script de migração:**
- `migrations/001_create_monitor_tables.sql`
- Popular com 3 monitores padrão (segurança, eficiência, fadiga)

### 1.2 API REST Endpoints (5 dias)

**Criar `server/monitor_api.py`:**

```python
# Monitores
POST   /api/monitors              # Criar monitor
GET    /api/monitors              # Listar todos
GET    /api/monitors/{id}         # Detalhes de um monitor
PUT    /api/monitors/{id}         # Atualizar monitor
DELETE /api/monitors/{id}         # Deletar monitor
POST   /api/monitors/{id}/toggle  # Ativar/desativar

# Veículos em Monitores
GET    /api/monitors/{id}/vehicles          # Veículos de um monitor
POST   /api/monitors/{id}/vehicles          # Adicionar veículo
DELETE /api/monitors/{id}/vehicles/{vid}    # Remover veículo

# Análises e Alertas
GET    /api/monitors/{id}/analyses     # Histórico de análises
GET    /api/alerts                     # Listar alertas (com filtros)
GET    /api/alerts/{id}                # Detalhes de um alerta
PUT    /api/alerts/{id}/acknowledge    # Reconhecer alerta
PUT    /api/alerts/{id}/resolve        # Resolver alerta
PUT    /api/alerts/{id}/dismiss        # Descartar alerta

# Estatísticas
GET    /api/monitors/stats             # Estatísticas gerais
GET    /api/alerts/stats               # Estatísticas de alertas
GET    /api/events/stats               # Estatísticas de eventos
GET    /api/events/catalog             # Catálogo de tipos de eventos
```

**Criar `server/monitor_db.py`:**
- Funções CRUD para tabelas de monitores
- Connection pooling MySQL
- Validações de dados

### 1.3 Sistema de Eventos (5 dias)

**Criar tabelas de eventos:**

```sql
-- Tipos de eventos (catálogo)
CREATE TABLE tipo_evento (
  id INT PRIMARY KEY AUTO_INCREMENT,
  codigo VARCHAR(50) UNIQUE,
  nome VARCHAR(100),
  categoria ENUM('critical', 'behavioral', 'operational'),
  severidade_padrao ENUM('low', 'medium', 'high', 'critical'),
  tempo_resposta_segundos INT,
  requer_acao_imediata BOOLEAN,
  usa_redis BOOLEAN,
  descricao TEXT
);

-- Eventos ocorridos
CREATE TABLE eventos (
  id INT PRIMARY KEY AUTO_INCREMENT,
  tipo_evento_id INT,
  veicod INT,
  timestamp DATETIME,
  latitude DOUBLE,
  longitude DOUBLE,
  dados_adicionais JSON,
  processado BOOLEAN DEFAULT FALSE,
  severidade ENUM('low', 'medium', 'high', 'critical'),
  FOREIGN KEY (tipo_evento_id) REFERENCES tipo_evento(id),
  INDEX idx_timestamp (timestamp),
  INDEX idx_processado (processado)
);
```

**Migrar detecção de eventos do `behavioral_engine.py`:**
- Atualmente eventos são in-memory (lista `vehicle_events`)
- MODIFICAR para salvar em tabela `eventos`
- Manter detecção existente: harsh_brake, harsh_accel, speeding, sharp_turn
- Adicionar 16 novos tipos de eventos gradualmente

**Criar agentes de detecção:**
- `event_agents/security_agents.py` - geofence, panic_button, tamper
- `event_agents/efficiency_agents.py` - excessive_idle, fuel_waste

---

## Fase 2: Monitor Engine - Scheduler & LLM (2 semanas)

### 2.1 Scheduler com APScheduler (3 dias)

**Criar `server/monitor_engine.py`:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from server.monitor_db import get_active_monitors

scheduler = BackgroundScheduler()

def schedule_monitors():
    monitors = get_active_monitors()
    for monitor in monitors:
        scheduler.add_job(
            func=run_monitor_analysis,
            args=[monitor['id']],
            trigger='interval',
            seconds=monitor['intervalo_analise'],
            id=f"monitor_{monitor['id']}"
        )

def run_monitor_analysis(monitor_id):
    # 1. Buscar veículos do monitor
    # 2. Buscar eventos nas últimas N horas (janela_contexto)
    # 3. Agrupar eventos por categoria (critical/behavioral/operational)
    # 4. Construir prompt para LLM
    # 5. Chamar LLM
    # 6. Salvar análise
    # 7. Gerar alertas se necessário
    pass
```

**Recursos:**
- Executar em processo separado: `python -m server.monitor_engine`
- Reload automático quando monitores são criados/editados
- Thread pool (10 workers) para análises paralelas

### 2.2 Integração LLM (OpenAI/Anthropic) (5 dias)

**Criar `server/llm_client.py`:**

```python
import openai
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    def __init__(self, model='gpt-4-turbo', temperature=0.3):
        self.model = model
        self.temperature = temperature
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def analyze(self, prompt: str, max_tokens: int = 500):
        if self.model.startswith('gpt'):
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            return {
                'content': response.choices[0].message.content,
                'tokens': response.usage.total_tokens,
                'model': self.model
            }
        elif self.model.startswith('claude'):
            # Implementar Anthropic
            pass
```

**Rate Limiting:**
- Implementar fila com limite de 20 RPM
- Tracking de custos por monitor
- Budget diário: parar se > $50/dia

**Context Builder:**

```python
class ContextBuilder:
    def build_monitor_context(self, monitor, vehicles, events):
        # Agrupar eventos por categoria
        grouped = {
            'critical': [e for e in events if e['categoria'] == 'critical'],
            'behavioral': [e for e in events if e['categoria'] == 'behavioral'],
            'operational': [e for e in events if e['categoria'] == 'operational']
        }

        # Estatísticas
        stats = {
            'total_eventos': len(events),
            'por_categoria': {k: len(v) for k, v in grouped.items()},
            'veiculos_com_eventos': len(set(e['device_id'] for e in events)),
            'evento_mais_critico': max(events, key=lambda e: severidade_to_int(e['severidade']))
        }

        # Preencher template do monitor
        prompt = monitor['prompt_template'].format(
            monitor_nome=monitor['nome'],
            total_veiculos=len(vehicles),
            janela_horas=monitor['janela_contexto'] / 3600,
            eventos_criticos=grouped['critical'],
            eventos_comportamentais=grouped['behavioral'],
            eventos_operacionais=grouped['operational'],
            estatisticas=stats
        )

        return prompt
```

### 2.3 Alert Generator (2 dias)

**Criar `server/alert_generator.py`:**

```python
def generate_alert(analysis_result, monitor, vehicle):
    # Parse LLM JSON response
    llm_data = json.loads(analysis_result['content'])

    # Decidir se gera alerta
    if not monitor['gera_alertas']:
        return None

    severidade = llm_data.get('severity', 'medium')
    if severidade_to_int(severidade) < monitor['severidade_minima']:
        return None  # Severidade abaixo do threshold

    # Criar alerta
    alert = {
        'analise_id': analysis_result['id'],
        'monitor_id': monitor['id'],
        'veiculomonitor_id': vehicle['id'],
        'titulo': llm_data.get('summary', 'Alerta gerado'),
        'mensagem': llm_data.get('detailed_message', ''),
        'severidade': severidade,
        'tipo': monitor['tipo_monitor'],
        'eventos_relacionados': analysis_result['eventos_analisados'],
        'status': 'pending'
    }

    # Salvar no banco
    alert_id = save_alert(alert)

    # Enviar notificações
    if monitor['notificar_gestor']:
        send_notification_to_manager(alert)
    if monitor['notificar_motorista']:
        send_notification_to_driver(alert)

    return alert_id
```

---

## Fase 3: Frontend - Integração Real (1 semana)

### 3.1 Substituir Mock Data por API Calls (3 dias)

**Criar `frontend/src/services/api.ts`:**

```typescript
import axios from 'axios';

const API_BASE = 'http://localhost:5009/api';

export const monitorService = {
  getAll: () => axios.get(`${API_BASE}/monitors`),
  getById: (id: number) => axios.get(`${API_BASE}/monitors/${id}`),
  create: (data: any) => axios.post(`${API_BASE}/monitors`, data),
  update: (id: number, data: any) => axios.put(`${API_BASE}/monitors/${id}`, data),
  delete: (id: number) => axios.delete(`${API_BASE}/monitors/${id}`),
  getVehicles: (id: number) => axios.get(`${API_BASE}/monitors/${id}/vehicles`),
  addVehicle: (id: number, vehicleData: any) =>
    axios.post(`${API_BASE}/monitors/${id}/vehicles`, vehicleData),
};

export const alertService = {
  getAll: (filters?: any) => axios.get(`${API_BASE}/alerts`, { params: filters }),
  getById: (id: number) => axios.get(`${API_BASE}/alerts/${id}`),
  acknowledge: (id: number) => axios.put(`${API_BASE}/alerts/${id}/acknowledge`),
  resolve: (id: number) => axios.put(`${API_BASE}/alerts/${id}/resolve`),
  dismiss: (id: number) => axios.put(`${API_BASE}/alerts/${id}/dismiss`),
};

export const eventService = {
  getCatalog: () => axios.get(`${API_BASE}/events/catalog`),
  getStats: () => axios.get(`${API_BASE}/events/stats`),
};
```

**Modificar componentes:**

```typescript
// MonitorDashboard.tsx
import { monitorService } from '../services/api';

const MonitorDashboard: React.FC = () => {
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    monitorService.getAll().then(res => {
      setMonitors(res.data);
      setLoading(false);
    });
  }, []);

  // Resto do componente...
};
```

**Fazer o mesmo para:**
- `AlertsPanel.tsx` → usar `alertService`
- `EventsCatalog.tsx` → usar `eventService`

### 3.2 WebSocket para Updates em Tempo Real (2 dias)

**Backend - `server/websocket_server.py`:**

```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

def broadcast_new_alert(alert):
    socketio.emit('new_alert', alert)

def broadcast_monitor_update(monitor_id):
    socketio.emit('monitor_updated', {'monitor_id': monitor_id})
```

**Frontend - `frontend/src/hooks/useWebSocket.ts`:**

```typescript
import { useEffect } from 'react';
import io from 'socket.io-client';

export const useWebSocket = (onNewAlert: (alert: any) => void) => {
  useEffect(() => {
    const socket = io('http://localhost:5009');

    socket.on('new_alert', (alert) => {
      onNewAlert(alert);
      // Show notification
      new Notification('Novo Alerta AI', {
        body: alert.titulo,
        icon: '/alert-icon.png',
      });
    });

    return () => socket.disconnect();
  }, [onNewAlert]);
};
```

### 3.3 UI para Criar/Editar Monitores (2 dias)

**Criar `frontend/src/components/MonitorEditor.tsx`:**

```typescript
interface MonitorEditorProps {
  monitorId?: number; // undefined = criar novo
  onSave: () => void;
  onCancel: () => void;
}

const MonitorEditor: React.FC<MonitorEditorProps> = ({ monitorId, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    tipo_monitor: 'safety',
    prompt_template: '',
    intervalo_analise: 300,
    // ... outros campos
  });

  const handleSubmit = async () => {
    if (monitorId) {
      await monitorService.update(monitorId, formData);
    } else {
      await monitorService.create(formData);
    }
    onSave();
  };

  return (
    <form>
      <input
        type="text"
        value={formData.nome}
        onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
        placeholder="Nome do Monitor"
      />
      {/* Mais campos... */}
      <button onClick={handleSubmit}>Salvar</button>
      <button onClick={onCancel}>Cancelar</button>
    </form>
  );
};
```

---

## Fase 4: Otimizações e Produção (1 semana)

### 4.1 Performance

- **Caching:** Redis para análises recentes (TTL 5 min)
- **Indexação:** Indexes em `eventos.timestamp`, `eventos.processado`
- **Batch Processing:** Analisar múltiplos veículos em um único prompt LLM

### 4.2 Segurança

- **API Authentication:** JWT tokens para endpoints de monitores
- **Rate Limiting:** Limitar API calls por usuário (100 req/min)
- **Input Validation:** Validar todos os inputs de formulários

### 4.3 Monitoramento

- **Logging:** Logs estruturados (JSON) com níveis (INFO, WARNING, ERROR)
- **Metrics:** Prometheus para tracking de:
  - Número de análises/hora
  - Tokens LLM consumidos
  - Latência de análises
  - Taxa de alertas gerados
- **Alerting:** Notificar admins se:
  - Custo LLM > $40/dia
  - Monitor Engine crashar
  - Taxa de erro LLM > 10%

### 4.4 Deployment

- **Docker:** Containerizar monitor engine separadamente
- **Systemd:** Auto-restart em falhas
- **Environment Variables:** Centralizar configs em `.env`

```bash
# docker-compose.yml
version: '3.8'
services:
  monitor-engine:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MYSQL_HOST=camerascasas.no-ip.info
      - MYSQL_PORT=3307
    restart: always
    depends_on:
      - mysql
```

---

## Fase 5: Expansão de Eventos (2 semanas)

Implementar os 16 eventos faltantes:

### Críticos (6 faltantes)
- `panic_button` - Webhook do rastreador
- `geofence_exit/entry` - Query de cercas virtuais no banco
- `tamper_detected` - Eventos do rastreador
- `theft_suspected` - Correlação de indicadores
- `collision_detected` - Acelerômetro
- `towing_detected` - Movimento sem ignição

### Comportamentais (3 faltantes)
- `fatigue_suspected` - Análise temporal de eventos
- `distracted_driving` - Padrões erráticos
- `aggressive_driving` - Score fuzzy < 50

### Operacionais (2 faltantes)
- `fuel_waste_detected` - Consumo acima do esperado
- `maintenance_due` - Threshold de km/tempo

**Para cada evento:**
1. Adicionar linha em `tipo_evento`
2. Criar agente de detecção
3. Inserir em `eventos` quando detectado
4. Testar com monitor

---

## Custos Estimados

### Desenvolvimento
- **Fase 1-3:** 6 semanas × 40h = 240 horas
- **Fase 4-5:** 3 semanas × 40h = 120 horas
- **Total:** 360 horas

### Operacionais (mensal)
- **LLM (GPT-4):** $9/mês (50 veículos, 60 análises/dia)
- **Infrastructure:** $0 (usando servidor existente)
- **Total:** ~$10/mês

### ROI Esperado
- **Redução de acidentes:** -20% (economia ~$5000/mês em seguros)
- **Economia de combustível:** -15% (economia ~$3000/mês)
- **ROI:** 800x em 1 mês

---

## Checklist de Implementação

### Fase 1: Backend
- [ ] Criar 4 tabelas de monitores
- [ ] Criar 2 tabelas de eventos
- [ ] Popular tipo_evento com 20 tipos
- [ ] Implementar API REST (10 endpoints)
- [ ] Migrar eventos de in-memory para DB
- [ ] Adicionar 4 novos agentes de eventos

### Fase 2: Monitor Engine
- [ ] Configurar APScheduler
- [ ] Integrar OpenAI API
- [ ] Implementar ContextBuilder
- [ ] Implementar AlertGenerator
- [ ] Rate limiting (20 RPM)
- [ ] Budget tracking ($50/dia)

### Fase 3: Frontend
- [ ] Criar apiService.ts
- [ ] Substituir mock em MonitorDashboard
- [ ] Substituir mock em AlertsPanel
- [ ] Substituir mock em EventsCatalog
- [ ] Implementar WebSocket
- [ ] Criar MonitorEditor
- [ ] Criar VehicleSelector

### Fase 4: Produção
- [ ] Indexar tabelas
- [ ] Configurar Redis caching
- [ ] Adicionar JWT auth
- [ ] Logging estruturado
- [ ] Prometheus metrics
- [ ] Dockerizar monitor engine

### Fase 5: Expansão
- [ ] Implementar 16 eventos faltantes
- [ ] Testes end-to-end
- [ ] Documentação de API
- [ ] Treinamento de usuários

---

## Próximos Passos Imediatos

**APÓS DEMONSTRAÇÃO PARA INVESTIDORES:**

1. **Aprovação do Budget** - Confirmar investimento
2. **Contratar OpenAI API** - Adquirir API key (Tier 2 ou superior)
3. **Kickoff Técnico** - Reunião com time de dev
4. **Sprint 1 (1 semana):**
   - Criar tabelas de banco de dados
   - Implementar 5 endpoints básicos de API
   - Substituir mock em 1 componente (MonitorDashboard)

**Meta Sprint 1:** Demonstração com 1 monitor real analisando 1 veículo

---

**Documento criado para:** Demonstração de Investidores - 10/02/2026 às 15h
**Versão Mock:** Totalmente funcional, dados simulados, zero custos
**Versão Real:** 9 semanas de desenvolvimento, $10/mês operacional, ROI 800x
