# Auditoria funcional — App "AITrack + DataDrivr"

> **Data:** 16/09/2026 · **Escopo:** `aitrackdatadrivr/` (frontend + backend) · **Commit:** `186050a`
> Todos os números abaixo foram **verificados** no banco `tracker@camerascasas:3307` e no código nesta data. Nenhum código foi alterado.

---

## 1. Sumário executivo

| Área | Situação |
|---|---|
| Rastreamento, mapa, posições | ✅ **Funciona** com dados reais |
| Detecção de eventos comportamentais | ✅ **Funciona** e grava no banco (2,6 milhões de eventos) |
| Score de motorista | ⚠️ **Roda, mas sem utilidade**: todos os veículos travados em **10.0** |
| **Monitores de IA** | ❌ **Não funcionam**: o motor nunca é iniciado, não há LLM, e a tela mostra dados falsos |
| Aba Alertas | ❌ **100% mock** (8 alertas fixos no código; botões não gravam nada) |
| Aba Eventos (catálogo) | ⚠️ Mock: mostra 20 tipos, só **4** existem |

**Resumo:** a interface dos monitores está pronta, mas a parte que analisa está desligada. A suspeita está **confirmada**, e há três causas independentes (seção 5).

---

## 2. As duas aplicações

| App | Pasta | Porta | Foco | Simulador |
|---|---|---|---|---|
| App 1 — AITrack | `aitrack/frontend` | 3001 | Mapa, rastreamento | `simulator.py` |
| **App 2 — AITrack + DataDrivr** | `aitrackdatadrivr/frontend` | **3003** | Comportamento, monitores de IA | `dirijabem_continuous_simulator.py` |
| Backend (compartilhado) | `aitrackdatadrivr/run.py` | API 5009, socket 9000 | — | — |

A porta 3000 está ocupada por outro projeto (`langnet-interface`).

---

## 3. Fluxo de dados real

```
Rastreador/simulador ──TCP 9000──▶ socket_server ──▶ protocol_parsers
                                                        │
                                                        ▼
                                  db_handler.save_location  ──▶ MySQL `localizacao` (4,29 mi)
                                                        │
                                   db_handler.py:119    ▼
                                  behavioral_engine.add_position
                                     ├─ detecta evento (4 tipos)
                                     ├─ score em MEMÓRIA   (vehicle_scores)
                                     ├─ lista em MEMÓRIA   (vehicle_events, nunca limpa)
                                     └─ grava ──▶ MySQL `eventos` (2,61 mi)

API Flask 5009 ──▶ /api/fleet/*  lê a MEMÓRIA
               ──▶ /api/monitors*, /api/alerts  lê TABELAS SEED

✗ RAMO MORTO:  monitor_engine.run() ──▶ analyze_monitor() ──▶ monitor_analises / monitor_alertas
               (nunca é chamado — ver seção 5)
```

`run.py` sobe **3 threads** (linhas 30–32): socket, API e replay do Dirijabem. **Nenhuma** delas é o motor de monitores.

---

## 4. Frontend do App 2, função por função

Legenda: ✅ real · ⚠️ real, mas com dados errados ou incompleto · ❌ mock

### 4.1 📊 Dashboard — `BehavioralDashboard.tsx` · ⚠️
| Função | Fonte | Situação |
|---|---|---|
| Seletor TRACKER | `GET /api/posicoes` (l.49), a cada 5 s | ✅ real |
| Seletor DIRIJABEM | `GET /api/dirijabem/users` (l.68) + `POST /user/{id}/start` (l.121) | ✅ real; inicia o replay da viagem |
| Score Médio / Veículos | `GET /api/fleet/stats` (l.83) → memória | ⚠️ real, mas **todos em 10.0** (seção 6.1) |
| "Eventos Hoje" | `fleet/stats.events_today` = `len(vehicle_events)` (`behavioral_engine.py:363`) | ⚠️ **não é "hoje"**: conta desde que o processo subiu. Na medição: memória **1.244.900**, banco de hoje **108.825** |
| Top Performers / Needs Attention | `GET /api/fleet/scores` (l.87) | ⚠️ sem sentido, porque todos estão empatados em 10 |
| Mapa | `MapComponent` | ✅ real |

### 4.2 ⏱️ Timeline — `EventsTimeline.tsx` · ✅
- `GET /api/fleet/events?limit=50` (l.24), a cada 5 s, lido da memória.
- Clicar num evento destaca o ponto no mapa. ✅
- Só existem 4 tipos de evento.

### 4.3 📈 Análises — `VehicleAnalytics.tsx` · ⚠️
- `GET /api/fleet/scores` (l.21) + `GET /api/fleet/events?limit=100` (l.24).
- A distribuição por tipo usa **apenas os últimos 100 eventos** da frota, não o histórico.
- A correlação score × eventos é prejudicada pelo score travado.

### 4.4 🤖 Monitores AI — `MonitorDashboard.tsx` · ⚠️/❌
| Função | Fonte | Situação |
|---|---|---|
| Lista de monitores (5) | `monitorService.getAll` → `/api/monitors` | ✅ real, mas é a **configuração seed** (`002_seed_monitors.sql`) |
| Detalhe do monitor | `getById` → `/api/monitors/{id}` | ✅ real |
| Veículos do monitor com score e status | `getVehicles` → `/api/monitors/{id}/vehicles` | ❌ **dados falsos**: sempre **score 85.0, 0 eventos, "ok"** (bug na seção 6.2) |
| **Análises da IA** | `monitorService.getAnalyses` existe (`apiService.ts:32`) | ❌ **nunca é chamado**; a tela não mostra análises |
| Ligar/desligar, criar ou editar monitor | endpoints `POST/PUT /api/monitors`, `/toggle` existem | ❌ **sem interface** |

### 4.5 Painel de detalhe do monitor — `MonitorDetailView.tsx` · ❌
- Eventos: `mockEvents` fixos, filtrados nas linhas 18 e 21. Nada vem do backend.
- Veículos: `mockVehiclesInMonitors`, passados por `App.tsx:140`.

### 4.6 🔔 Alertas — `AlertsPanel.tsx` · ❌
| Função | Situação |
|---|---|
| Lista de alertas | `mockAlerts`: **8 alertas escritos no código** (`mockAlerts.ts`) |
| KPIs do cabeçalho | `mockAlertStats`, fixos |
| Filtros de status/severidade | ✅ funcionam, mas sobre o mock |
| **Reconhecer** (l.28) | ❌ só abre `alert('Alerta reconhecido! (Mock - não persiste)')` |
| **Resolver** (l.34) | ❌ só abre `alert('Alerta resolvido! (Mock - não persiste)')` |
| Integração real | `alertService` (`apiService.ts:59–90`) tem `getAll`, `acknowledge`, `resolve`, `dismiss` e `getStats` **prontos e sem uso** |

Os **4 alertas reais do banco** (também seed) **nunca aparecem** na tela.

### 4.7 📋 Eventos — `EventsCatalog.tsx` · ❌
- Catálogo de **20 tipos** e estatísticas vindos de `mockEvents.ts`.
- O banco (`tipo_evento`) tem **4**: `harsh_accel`, `harsh_brake`, `sharp_turn`, `speeding`.
- `/api/events/catalog` e `/api/events/stats` existem e não são usados.

### 4.8 Componentes de apoio
| Componente | Situação |
|---|---|
| `MapComponent.tsx` | ✅ 7 chamadas reais: posições, scores, eventos, trilha, rota e último ponto do Dirijabem |
| `MapViewUpdater.tsx` | ✅ ajusta o zoom aos pontos |
| `VehicleList.tsx` | ✅ real, mas **não é usado** no `App.tsx` (código morto) |
| `App.tsx` | ✅ navegação; ❌ injeta `mockVehiclesInMonitors` |

**Placar do frontend:** de 6 abas, **2 são reais** (Timeline, mapa), **2 são reais com dados distorcidos** (Dashboard, Análises) e **2 são mock** (Alertas, Eventos). A aba Monitores mistura partes reais e falsas.

---

## 5. Por que os monitores de IA não funcionam

### Causa 1 — O motor nunca é iniciado
- `server/monitor_engine.py` está **completo**: `run()` → `schedule_monitors()` → `analyze_monitor()`.
- As gravações `monitor_db.save_analysis` (INSERT, l.328) e `create_alert` (INSERT, l.394) estão **implementadas**.
- Mas `monitor_engine` **não é importado em nenhum lugar**. `run.py` não o inicia.
- **Evidência:** `monitor_analises` tem **0 linhas** desde fevereiro.

**Teste feito:** o `analyze_monitor(1)` real foi executado lendo a configuração do banco, com todas as gravações interceptadas (nada foi escrito). Com eventos na janela, ele **gerou 2 análises e 2 alertas** `critical`:
```
critical | Score 10.0 - 22 eventos em 30 min. Mais frequentes: harsh_accel (12), harsh_brake (10)
```
Portanto o motor **funciona quando é executado**. O problema é só que ninguém o executa.

> Ele precisa rodar **no mesmo processo** do `run.py`, porque lê scores e eventos da **memória** do `behavioral_engine`. Um processo separado enxergaria tudo vazio.

### Causa 2 — Não existe IA (LLM)
- O código diz isso explicitamente: `"Versão simplificada (sem LLM)"` (`monitor_engine.py:4, 135`).
- A "análise" são 3 regras de limite (`score < 50` → critical, `< 60` → high) e uma contagem de tipos (l.50–68).
- `anthropic` e `openai` estão **comentados** em `requirements-monitors.txt`.
- O schema **não tem** as colunas previstas no `PLAN_AI_MONITORS.md` (`prompt_template`, `modelo_llm`, resposta do LLM, tokens). O banco usa a versão simplificada.

### Causa 3 — A tela não mostra o que o motor produziria
- A aba Monitores **não chama** `getAnalyses`.
- A aba Alertas usa **mock** e não lê `monitor_alertas`.
- O status dos veículos é um **fallback fixo** de 85/"ok" (seção 6.2).

Mesmo se o motor fosse ligado hoje, **nada mudaria na tela**.

---

## 6. Outros problemas encontrados

### 6.1 Score travado no piso (grave)
- `update_score` só **subtrai** e nunca recupera. O piso é 10 (`behavioral_engine.py`, `update_score`).
- **Medido:** os 10 veículos estão em **10.0**. Média da frota **10.0**.
- Isso acontece porque a detecção compara com **amostras**, não com tempo:
  - `harsh_accel`/`harsh_brake` comparam com a posição de 2 amostras antes (`list(history)[-3]`), apesar do comentário "em 3 segundos".
  - O simulador envia a cada ~10 s com velocidade sorteada entre 20 e 60 km/h (`simulator.py:49`). Isso gera frenagens e acelerações "bruscas" falsas o tempo todo.

### 6.2 Import quebrado na API de monitores
- `monitor_api.py:86`: `from behavioral_engine import ...`. Sem o pacote `server.`, o módulo não existe.
- **Verificado:** `ModuleNotFoundError: No module named 'behavioral_engine'`.
- O `except ImportError` (l.113–117) devolve **score 85.0, 0 eventos, "ok"** para todos.
- O mesmo import errado aparece em `monitor_api.py:290` (`/api/events/stats`). Ali o fallback lê o banco, então o efeito é menor.

### 6.3 Consumo de memória crescente
- `vehicle_events` é uma lista **sem limite**. Já `vehicle_history` usa `deque(maxlen)` e é limitado.
- **Medido:** backend com **~1,05 GB de RAM** depois de 8 dias, com 1,24 milhão de eventos em memória.
- `get_recent_events` percorre a lista inteira a cada requisição, e o mapa consulta a cada 3 s. O custo cresce com o tempo.

### 6.4 Volume de alertas se o motor fosse ligado sem ajustes
Com scores em 10, todo ciclo de todo veículo vira `critical`:

| Monitor | Veículos | Intervalo | Análises/alertas por hora |
|---|---|---|---|
| #1 | 2 | 5 min | 24 |
| #2 | 2 | 10 min | 12 |
| #3 | 2 | 15 min | 8 |
| #4 | 3 | 5 min | 36 |
| #5 | 1 | inativo | 0 |
| **Total** | | | **80/h ≈ 1.920/dia** |

Não existe deduplicação nem cooldown. Com LLM, seriam 80 chamadas por hora repetindo a mesma conclusão.

### 6.5 Cobertura
- **4 de 20** tipos de evento são detectados.
- Os monitores só cobrem veículos **tracker**. O Dirijabem (app) não alimenta o `behavioral_engine`, então motoristas do app nunca são analisados pelos monitores.
- Tabelas seed nunca atualizadas: `monitores` (5), `veiculomonitor` (10), `monitor_alertas` (4), `veiculo_unificado` (20), `tipo_evento` (4).

---

## 7. Estado do banco (16/09/2026)

| Tabela | Linhas | Origem |
|---|---|---|
| `localizacao` | 4.294.434 | ✅ runtime |
| `eventos` | 2.609.405 (108.825 hoje) | ✅ runtime (`behavioral_engine`) |
| `veiculos` | 5.218 | runtime + legado |
| `monitor_analises` | **0** | ❌ nunca populada |
| `monitor_alertas` | **4** | 🌱 seed `004_seed_mock_alerts.sql` |
| `monitores` | 5 | 🌱 seed `002_seed_monitors.sql` |
| `veiculomonitor` | 10 | 🌱 seed |
| `tipo_evento` | 4 | 🌱 seed `003_create_eventos_table.sql` |
| `veiculo_unificado` | 20 | 🌱 seed `004_create_veiculo_unificado.sql` |

---

## 8. O que falta — roteiro até monitores com LLM Claude

A ordem importa. Sem a Fase 0, o LLM analisaria scores sem significado.

### Fase 0 — Corrigir a base (pré-requisito)
1. Corrigir os imports em `monitor_api.py:86` e `:290` para `from .behavioral_engine import ...`.
2. Refazer o score: calcular por **janela deslizante** (eventos dos últimos N minutos) ou permitir recuperação com o tempo. Assim ele volta a diferenciar motoristas.
3. Detectar eventos pelo **tempo real** entre amostras (Δv/Δt), não pela quantidade de amostras.
4. Limitar `vehicle_events` (deque ou janela temporal) e calcular "eventos hoje" de verdade (banco ou filtro por data).
5. Tornar o simulador tracker realista (velocidade contínua, não sorteada a cada pacote).

### Fase 1 — Ligar o motor (rule-based)
6. Iniciar `monitor_engine.run()` como **4ª thread** em `run.py`, no mesmo processo.
7. Adicionar **cooldown e deduplicação** de alertas (por exemplo, não repetir alerta aberto do mesmo veículo e monitor).
8. Resultado esperado: `monitor_analises` passa a crescer, e alertas reais aparecem via API.

### Fase 2 — Análise com LLM Claude
9. **Migration**:
   - em `monitores`: `modelo_llm`, `prompt_template`, `temperatura`;
   - em `monitor_analises`: `resposta_llm`, `recomendacoes`, `tokens_entrada`, `tokens_saida`, `tempo_ms`.
10. Criar `server/llm_client.py` com o SDK `anthropic` (já instalado; descomentar em `requirements-monitors.txt`) e `ANTHROPIC_API_KEY` em `config/.env`.
11. Em `analyze_monitor`, **manter as regras como pré-filtro** (l.34–48: só analisa se score < limite e eventos ≥ mínimo). Trocar o bloco das l.50–68 por uma chamada ao Claude com **saída estruturada** (severidade, conclusão, padrões, recomendações).
12. Controle de custo: modelo por monitor (sugestão: `claude-haiku-4-5` como padrão, `claude-opus-5` para casos críticos), timeout, e fallback para as regras se a API falhar.

### Fase 3 — Frontend real
13. **Alertas:** trocar `mockAlerts`/`mockAlertStats` por `alertService.getAll/getStats`. Ligar Reconhecer, Resolver e Descartar a `acknowledge/resolve/dismiss`.
14. **Monitores:** mostrar análises (`getAnalyses`) e recomendações do LLM. Adicionar ligar/desligar, criar e editar monitor.
15. **Detalhe do monitor:** trocar `mockEvents` por `/api/fleet/events?device_id=` ou `/api/events`. Remover `mockVehiclesInMonitors` do `App.tsx`.
16. **Eventos:** usar `/api/events/catalog` e `/api/events/stats`.
17. Remover `VehicleList.tsx` (sem uso) e a pasta `mockData/` quando ficar sem referências.

### Fase 4 — Cobertura
18. Implementar os 16 tipos de evento restantes do catálogo, conforme `MONITORAMENTO_EVENTOS.md`.
19. Incluir motoristas Dirijabem nos monitores (alimentar o motor com as viagens do app).

---

## 9. Como reproduzir esta auditoria

```bash
cd aitrackdatadrivr

# motor nunca referenciado fora do próprio arquivo
grep -rn monitor_engine --include=*.py . | grep -v server/monitor_engine.py

# run.py: só 3 threads
grep -n "Thread(" run.py

# import quebrado
python3 -c "from behavioral_engine import get_vehicle_score"   # ModuleNotFoundError

# API ao vivo
curl -s localhost:5009/api/monitors/stats        # total_analises: 0
curl -s localhost:5009/api/fleet/scores          # todos 10
curl -s localhost:5009/api/monitors/1/vehicles   # score_atual 85.0 (fallback)
curl -s localhost:5009/api/alerts                # 4 alertas seed

# mocks no frontend
grep -rn "mockData" frontend/src --include=*.tsx | grep import
```

SQL: `SELECT COUNT(*)` em `monitor_analises` (0), `monitor_alertas` (4) e `eventos` (milhões).

---

## Anexo — Endpoints existentes × usados pelo App 2

| Endpoint | Existe | Usado pela tela |
|---|---|---|
| `GET /api/posicoes` | ✅ | ✅ |
| `GET /api/fleet/stats`, `/scores`, `/events` | ✅ | ✅ |
| `GET /api/positions/latest/{veicod}` | ✅ | ✅ |
| `GET /api/dirijabem/users`, `POST /user/{id}/start`, `/route`, `/last-point` | ✅ | ✅ |
| `GET /api/monitors`, `/{id}`, `/{id}/vehicles` | ✅ | ✅ |
| `GET /api/monitors/{id}/analyses` | ✅ | ❌ |
| `POST/PUT /api/monitors`, `/{id}/toggle`, gestão de veículos | ✅ | ❌ |
| `GET /api/monitors/stats` | ✅ | ❌ |
| `GET /api/alerts`, `/{id}`, `/stats` | ✅ | ❌ |
| `PUT /api/alerts/{id}/acknowledge`, `/resolve`, `/dismiss` | ✅ | ❌ |
| `GET /api/events`, `/catalog`, `/stats` | ✅ | ❌ |
| `GET /api/vehicles/unified`, `/api/monitors/{id}/vehicles/unified` | ✅ | ❌ |
| `GET /api/unified/vehicles`, `/api/unified/position/{placa}` | ✅ | ❌ (usados pelo App 1) |
