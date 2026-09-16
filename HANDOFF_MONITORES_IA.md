# HANDOFF — Monitores de IA do App "AITrack + DataDrivr"

> **Para quem é:** um agente de código (Codex ou outro) que vai assumir o desenvolvimento **sem contexto prévio**.
> **Escrito em:** 16/09/2026, a partir do commit `186050a`, com o sistema rodando e o banco inspecionado.
> **Pré-leitura obrigatória:** `AGENTS.md` (regras, ambiente, segurança do banco, git) e `AUDITORIA_APP2_DATADRIVR.md` (diagnóstico).
> **Este documento é a fonte de verdade do QUE fazer.** As decisões de projeto já foram tomadas e estão escritas em cada tarefa. Siga-as. Se uma decisão se mostrar inviável na prática, registre o motivo no "Registro de progresso" (seção 10) antes de desviar.

---

## Índice
0. Como trabalhar com este documento
1. Objetivo final
2. Resumo do sistema atual
3. Referência do banco de dados
4. **Fase 0: corrigir a base**
5. **Fase 1: ligar o motor de monitores (regras)**
6. **Fase 2: análise com Claude (LLM)**
7. **Fase 3: frontend real (sem mock)**
8. **Fase 4: cobertura de eventos e motoristas do app**
9. Definição de pronto global
10. Registro de progresso (atualize a cada tarefa)
- Apêndice A: endpoints (atuais e novos)
- Apêndice B: comandos úteis de diagnóstico

---

## 0. Como trabalhar com este documento

1. Execute as fases **na ordem** (0 → 1 → 2 → 3 → 4). Dentro de cada fase, siga a ordem das tarefas, salvo indicação contrária.
2. Cada tarefa tem: **Problema** (com evidência), **Arquivos**, **O que fazer**, **Critério de aceite** e **Como verificar**.
3. **Um commit por tarefa**, com o ID da tarefa na mensagem, e push na `main` (ver `AGENTS.md` §5).
4. Ao terminar cada tarefa, **adicione uma linha na seção 10**. Se parar no meio, registre o estado.
5. Números de linha citados valem para o commit `186050a`. Eles mudam conforme você edita. Localize pelo nome da função.
6. Não pule critérios de aceite. Se um não puder ser atingido, registre o motivo na seção 10 e siga.
7. O usuário não impôs limite de custo à API da Claude, mas **não desperdice**: chamadas ao LLM só acontecem quando as regras indicam que há algo a analisar (Fase 2).

---

## 1. Objetivo final

Ao final das 5 fases:
- O **score de motorista** diferencia bons e maus motoristas e se recupera com o tempo.
- Eventos comportamentais são detectados por **taxa real** (Δv/Δt, Δrumo/Δt) e persistidos com eficiência.
- O **motor de monitores roda** dentro do backend, analisa periodicamente os veículos de cada monitor ativo, usa **Claude (`claude-opus-5`)** para produzir análise estruturada em português e gera **alertas reais**, sem duplicatas.
- O App 2 mostra **apenas dados reais**: alertas do banco com Reconhecer/Resolver/Descartar funcionando, análises da IA visíveis, catálogo de eventos do banco. A pasta `mockData/` não existe mais.
- O catálogo de **20 tipos de evento** está no banco. Os detectáveis com os dados disponíveis estão implementados; os inviáveis estão marcados como tal.
- Motoristas do **app Dirijabem** podem ser incluídos em monitores.
- O **App 1** (porta 3001) continua funcionando sem regressão.

---

## 2. Resumo do sistema atual (o essencial da auditoria)

**Processos** (todos iniciados a partir de `aitrackdatadrivr/`):
- `run.py`: 3 threads no mesmo processo: socket TCP 9000 (`server/socket_server.py`), API Flask 5009 (`server/api.py` + blueprints), replay Dirijabem (`dirijabem_simulator.get_replay_manager`).
- `simulator.py`: 10 veículos `SIM-1000`…`SIM-1009`, 1 pacote a cada 5 s. Perfis: `SIM-1000..1004` = good, `SIM-1005..1007` = moderate, `SIM-1008..1009` = poor.
- `dirijabem_continuous_simulator.py`: grava viagens sintéticas em `dirijabem.viagem` e `dirijabem.localizacaodados`.

**Fluxo de uma posição:**
```
pacote TCP → socket_server.handle_connection → protocol_parsers.parse_data
  → db_handler.save_location
      ├─ INSERT tracker.localizacao
      └─ behavioral_engine.add_position(device_id, {lat, lon, speed, heading, timestamp=datetime.now()})
            ├─ detect_events (compara com amostras anteriores)
            ├─ update_score (só subtrai; piso 10)
            ├─ vehicle_events.append (lista em memória SEM LIMITE)
            └─ save_event_to_db (1 conexão nova por evento) → tracker.eventos
```

**Blueprints da API:**
- `server/api.py`: `/api/posicoes`, `/api/positions/*`, `/api/fleet/*`, `/api/vehicles/<id>/score`
- `server/monitor_api.py`: `/api/monitors*`, `/api/alerts*`, `/api/events*`, `/api/vehicles/unified`
- `server/unified_api.py` (prefixo `/api/unified`): usado pelo App 1
- `server/dirijabem_api.py` (prefixo `/api/dirijabem`)

**Módulos do motor de monitores:**
- `server/monitor_engine.py`: `run()` → `schedule_monitors()` → `analyze_monitor()`. **Nunca é iniciado.** Análise por regras, sem LLM.
- `server/monitor_db.py`: CRUD de `monitores`, `veiculomonitor`, `monitor_analises` (`save_analysis`), `monitor_alertas` (`create_alert`, `acknowledge_alert`, `resolve_alert`, `dismiss_alert`, `get_alert_stats`, `get_monitor_stats`). As funções de gravação **funcionam**.

**Problemas a resolver** (detalhes na auditoria):

| # | Problema | Evidência | Tarefa |
|---|---|---|---|
| 1 | Todos os scores travados em 10 | `/api/fleet/scores` → todos 10 | T0.5, T0.6 |
| 2 | Detecção por nº de amostras; rumo sorteado pelo simulador | `behavioral_engine.detect_events`, `simulator.py` (heading `random.uniform`) | T0.5, T0.9 |
| 3 | Import quebrado → score falso 85 na aba Monitores | `monitor_api.py:86,290` | T0.3 |
| 4 | Lista de eventos em memória sem limite (~1 GB RAM) | `behavioral_engine.vehicle_events` | T0.4 |
| 5 | 1 conexão MySQL por evento, síncrona no socket | `save_event_to_db` | T0.7 |
| 6 | `/api/events` 18,8 s e `/api/events/stats` 15,7 s | `DATE(e.timestamp)=CURDATE()` | T0.8 |
| 7 | "Eventos Hoje" conta desde o start do processo | `get_fleet_stats` usa `len(vehicle_events)` | T0.8 |
| 8 | Credenciais escritas em 8 arquivos (2 usuários) | `grep -rn DB_CONFIG` | T0.2 |
| 9 | Motor de monitores nunca iniciado | `run.py` não o importa | T1.3 |
| 10 | Sem deduplicação de alertas (~1.920/dia previstos) | `analyze_monitor` | T1.4 |
| 11 | Sem LLM | `monitor_engine.py:4` | Fase 2 |
| 12 | Alertas, Detalhe do monitor e Eventos são mock | `mockData/` | Fase 3 |
| 13 | 4/20 tipos de evento; app Dirijabem fora dos monitores | `tipo_evento` | Fase 4 |

---

## 3. Referência do banco de dados

Servidor **MariaDB 10.3.39** em `camerascasas.no-ip.info:3307`. Leia as regras de segurança em `AGENTS.md` §4.

### 3.1 Banco `tracker` (escrita permitida)

**`veiculos`** (latin1): `VEICOD` PK, `VEI_DEVICE_ID` UNIQUE, `VEIPLACA`, `VEIMODELO`, `FK_USUCOD`, `VEI_CHIP_NUMERO`, `FK_TMOD_COD`.

**`localizacao`** (~4,3 mi): `FK_VEICOD`, `LOCLATLONG` (GEOMETRY, use `ST_X`/`ST_Y`), `DATAHORA`, `VELATU`, `ALTITUDE`, `ORIENT`.

**`tipo_evento`** (4 linhas: `harsh_brake`=1, `harsh_accel`=2, `speeding`=3, `sharp_turn`=4):
`id`, `codigo` UNIQUE, `nome`, `categoria` ENUM('critical','behavioral','operational'), `severidade_padrao` ENUM('low','medium','high','critical'), `icone` (texto curto, ex.: 'accel', **não** é emoji), `cor`, `descricao`.

**`eventos`** (~2,6 mi; +~100 mil/dia; datas de 03/03/2026 até hoje):
```
id PK AI · tipo_evento_id INT NOT NULL FK→tipo_evento · veicod INT NOT NULL FK→veiculos.VEICOD
device_id VARCHAR(50) · timestamp DATETIME NOT NULL · latitude DOUBLE · longitude DOUBLE · velocidade FLOAT
dados_adicionais LONGTEXT(JSON) · severidade ENUM('low','medium','high','critical') NOT NULL · processado TINYINT DEFAULT 0
Índices: idx_timestamp(timestamp), idx_device(device_id), idx_veicod(veicod), idx_processado, tipo_evento_id
```

**`monitores`** (5 linhas seed):
`id`, `nome`, `descricao`, `tipo_monitor` ENUM('safety','efficiency','compliance','predictive','custom'), `intervalo_analise` INT (s), `janela_contexto` INT (s), `eventos_minimos` INT, `score_threshold` FLOAT, `gera_alertas` BOOL, `ativo` BOOL, `criado_em`, `atualizado_em`.

| id | ativo | intervalo | janela | mín. eventos | limite score | veículos (veiculomonitor) |
|---|---|---|---|---|---|---|
| 1 | 1 | 300 s | 1800 s | 3 | 70 | SIM-1000, SIM-1001 |
| 2 | 1 | 600 s | 3600 s | 5 | 75 | SIM-1002, SIM-1003 |
| 3 | 1 | 900 s | 5400 s | 4 | 80 | SIM-1004, SIM-1005 |
| 4 | 1 | 300 s | 1800 s | 2 | 65 | SIM-1006, SIM-1007, SIM-1008 |
| 5 | 0 | 1800 s | 7200 s | 6 | 70 | SIM-1009 |

**`veiculomonitor`**: `id`, `monitor_id` FK CASCADE, `tipo_veiculo` ENUM('tracker','dirijabem'), `veicod_tracker` FK, `codusu_dirijabem`, `device_id`, `ativo`, `atribuido_em`. UNIQUE `(monitor_id, veicod_tracker)` e `(monitor_id, codusu_dirijabem)`.

**`monitor_analises`** (0 linhas): `id`, `monitor_id`, `veiculomonitor_id`, `analisado_em` DEFAULT now, `periodo_inicio` NOT NULL, `periodo_fim` NOT NULL, `total_eventos`, `score_inicial`, `score_final`, `eventos_por_tipo` (JSON), `conclusao` TEXT, `severidade` ENUM. Índice `(monitor_id, analisado_em)`.

**`monitor_alertas`** (4 linhas seed de 27/02/2026, `analise_id` NULL):
`id`, `analise_id` FK SET NULL, `monitor_id`, `veiculomonitor_id`, `device_id`, `nome_motorista`, `titulo` NOT NULL, `mensagem`, `severidade` ENUM, `tipo` ENUM('behavior','safety','efficiency','compliance','prediction'), `criado_em`, `status` ENUM('pending','acknowledged','resolved','dismissed') DEFAULT 'pending', `reconhecido_em`, `reconhecido_por`, `total_eventos_relacionados`.

**`veiculo_unificado`** (20 linhas): `id`, `device_id`, `codusu`, `placa`, `descricao`, `tipo` ENUM('tracker_only','app_only','both'), `ativo`. Linhas app: `SIM-D1` (codusu 1), `SIM-D2` (614), `SIM-D3` (17)…, com `device_id` NULL. **Usada pelo App 1: não altere dados existentes.**

**`geocercas`** (0 linhas): `GCER_COD`, `GCER_NOME`, `GCER_AREA` POLYGON, `FK_USUCOD`.

### 3.2 Banco `dirijabem` (somente leitura)

- **`viagem`** (~81 mil): `CODVIA` PK, `CODUSU` (idx), `PLACA` (idx), `DATAHORINI`, `DATAHORFIN`, `DISTANCIA`, `DURACAO`, `SCORE`, métricas `OST, OSA, GAA, OSP, SAM, SAA, BRP, BRM, BRA, GAP, GAN, GAM`.
- **`localizacaodados`** (~60 mi): `LOCDADCOD` PK, `CODVIA` (idx), `DATAHORA`, `VELATU`, `ACELLINATU`, `ACELGPSATU`, `VARDIRATU`, `coords`. **Só existem índices em `LOCDADCOD` e `CODVIA`.** Consulte sempre por `CODVIA IN (...)` e/ou `LOCDADCOD > x`.

---

## 4. FASE 0 — Corrigir a base

**Por que primeiro:** hoje o score é inútil (todos em 10), a detecção gera eventos falsos e as consultas de eventos são lentas. Qualquer análise por regras ou LLM sobre esses dados seria lixo.

### T0.1 — Ambiente isolado, dependências e runner de migrations

**Problema:** o backend usa o Python global do miniconda, compartilhado com outros projetos. O `anthropic` instalado é 0.57.1, e a Fase 2 precisa de ≥ 1.6.0; atualizar no global quebraria outros projetos. Não há controle de quais migrations foram aplicadas.

**O que fazer:**
1. Criar `aitrackdatadrivr/.venv`: `python3 -m venv .venv`.
2. Criar `aitrackdatadrivr/requirements.txt`, consolidando `requirements-monitors.txt` e `requirements-tests.txt` da raiz, além do que o código importa:
   ```
   flask>=3.0
   flask-cors>=4.0
   mysql-connector-python>=8.0
   anthropic>=1.6.0,<2
   pydantic>=2.5
   pytest>=8.0
   requests>=2.31
   playwright>=1.40
   ```
   Antes de fechar a lista, confira com `grep -rhE "^(import|from) " --include=*.py aitrackdatadrivr | sort -u` se algum pacote ficou faltando.
   Os simuladores Dirijabem podem importar pacotes extras.
   Remova `schedule`, que deixa de ser usado em T1.3; se ainda for importado antes de T1.3, mantenha até lá.
3. `pip install -r requirements.txt` **dentro do venv**.
4. Adicionar ao `.gitignore` da raiz: `aitrackdatadrivr/.venv/`, `aitrackdatadrivr/migrations/backup/`, `aitrackdatadrivr/frontend/build/`.
5. Criar `aitrackdatadrivr/migrations/apply.py`:
   - Lê credenciais pelo `server/db_config.py` (T0.2). Se T0.2 ainda não existir, faça T0.2 junto neste commit.
   - Garante `tracker.schema_migrations (versao VARCHAR(100) PRIMARY KEY, aplicada_em DATETIME DEFAULT CURRENT_TIMESTAMP)`.
   - Na primeira execução, registra `001_create_monitor_tables.sql`, `002_seed_monitors.sql`, `003_create_eventos_table.sql`, `004_create_veiculo_unificado.sql` e `004_seed_mock_alerts.sql` **como já aplicadas, sem executá-las**.
   - Aplica, em ordem alfabética, os `.sql` pendentes com o cliente `mysql` via `subprocess`. Credenciais vão num arquivo temporário `--defaults-extra-file` com `chmod 600`, apagado ao final. **Nunca** passe a senha na linha de comando.
   - Após sucesso, insere a versão em `schema_migrations`. Em erro, para e mostra a saída.
   - Flags: `--dry-run` lista as pendentes; `--baseline-only` só registra as já aplicadas.
6. Atualizar `AGENTS.md` §3.2 e §3.6 se algum comando mudar.

**Critério de aceite:**
- `.venv/bin/python -c "import anthropic, pydantic, flask; print(anthropic.__version__)"` mostra ≥ 1.6.0.
- O Python global continua com `anthropic` 0.57.1: `/home/pasteurjr/miniconda3/bin/python3 -c "import anthropic; print(anthropic.__version__)"`.
- `python migrations/apply.py --dry-run` roda e, após o baseline, lista 0 pendentes.
- O backend sobe com `.venv/bin/python run.py` e `/api/monitors` responde.

### T0.2 — Configuração de banco centralizada

**Problema:** credenciais estão escritas em `server/behavioral_engine.py`, `server/monitor_db.py`, `server/api.py`, `server/db_handler.py`, `server/unified_api.py`, `server/dirijabem_api.py`, `dirijabem_simulator.py` e `extract_dirijabem_routes.py`. São dois usuários: `scadabr` para `tracker` e `producao` para `dirijabem`/unificado. Além disso, `env_loader.load_dotenv` e `routes_loader.load_routes` usam caminhos relativos ao diretório atual.

**O que fazer:**
1. Criar `server/db_config.py`:
   ```python
   # carrega config/.env de forma robusta (relativo a este arquivo, não ao cwd)
   BASE_DIR = Path(__file__).resolve().parent.parent   # aitrackdatadrivr/
   load_dotenv(paths=(BASE_DIR / "config/.env",))
   def _req(name): ...   # erro claro se ausente: "Variável X ausente em config/.env"
   TRACKER_DB = {host, port, user, password, database}      # AITRACK_DB_*
   DIRIJABEM_DB = {host, port, user, password, database}    # DIRIJABEM_DB_* (DIRIJABEM_DB_NAME default 'dirijabem')
   def get_tracker_pool() -> MySQLConnectionPool   # singleton, pool_name="tracker_pool", pool_size=20, criado sob lock
   def tracker_conn(): return get_tracker_pool().get_connection()
   def dirijabem_conn(): return mysql.connector.connect(**DIRIJABEM_DB)
   ```
   - Senhas **sem default** no código.
   - Host/porta podem ter default igual ao atual.
2. Ajustar `server/env_loader.load_dotenv` para aceitar `Path`. Ajustar `server/routes_loader.load_routes` para usar `BASE_DIR / "config/routes.json"`.
3. Adicionar ao `aitrackdatadrivr/config/.env` as chaves `DIRIJABEM_DB_HOST`, `DIRIJABEM_DB_PORT`, `DIRIJABEM_DB_USER`, `DIRIJABEM_DB_PASSWORD` e `DIRIJABEM_DB_NAME`, com os valores que hoje estão no código (usuário `producao`). Esse arquivo é ignorado pelo git.
4. Criar `aitrackdatadrivr/config/.env.example` com **todas** as chaves e valores vazios, incluindo as da Fase 2 (`ANTHROPIC_API_KEY`, `LLM_*`). Esse arquivo é versionado.
5. Substituir **todos** os `DB_CONFIG` e `TRACKER_DB_CONFIG`/`DIRIJABEM_DB_CONFIG` pelo `db_config`. `unified_api` passa a usar `TRACKER_DB` (usuário `scadabr`) para o `tracker`.
6. `db_handler.py` passa a usar `get_tracker_pool()` em vez do pool próprio.

**Critério de aceite:**
- `grep -rnE "'password'\s*:\s*'" --include=*.py aitrackdatadrivr` retorna **nada**.
- Backend iniciado **a partir de outro diretório** (`cd / && /home/.../aitrackdatadrivr/.venv/bin/python /home/.../aitrackdatadrivr/run.py`) sobe e responde.
- App 1 ok: `/api/unified/vehicles` retorna 20 veículos e `/api/unified/position/SIM-D1` responde.
- App 2 ok: `/api/dirijabem/users` retorna usuários.

### T0.3 — Corrigir imports quebrados em `monitor_api.py`

**Problema:**
- `monitor_api.py:86` faz `from behavioral_engine import get_vehicle_score, get_recent_events`. Isso gera `ModuleNotFoundError`, e o `except ImportError` (l.113–117) devolve **score 85.0, 0 eventos, 'ok'** para todos.
- Mesmo import em `:290` (`/api/events/stats`).

**O que fazer:**
1. Trocar por `from . import behavioral_engine` no topo do módulo e usar `behavioral_engine.get_vehicle_score(...)`.
2. **Remover** os fallbacks silenciosos com valores inventados. Em erro real, logar com `logging.exception` e retornar os veículos sem enriquecimento, com `score_atual: null` e `status: "desconhecido"`. Ajustar o frontend no mesmo commit, se necessário.
3. A contagem `total_eventos_hoje` por veículo passa a vir do banco (ver T0.8), não da lista em memória.

**Critério de aceite:** `/api/monitors/1/vehicles` → `score_atual` igual ao de `/api/fleet/scores` para `SIM-1000`/`SIM-1001` (tolerância de 1 ciclo de 5 s).

### T0.4 — Estado em memória: limite e thread safety

**Problema:**
- `vehicle_events` é `List` sem limite (1,24 mi itens, ~1 GB).
- Estado acessado por threads do socket (20 workers), da API e, a partir da Fase 1, do motor, sem lock.
- `get_recent_events(device_id=...)` varre a lista inteira a cada chamada.

**O que fazer** (em `server/behavioral_engine.py`):
1. `_lock = threading.RLock()`. Toda leitura e escrita de `vehicle_history`, `vehicle_scores`, `vehicle_events` e dos novos índices ocorre sob o lock. Leituras devolvem **cópias** (`list(...)`, `dict(...)`).
2. `vehicle_events` → `deque(maxlen=EVENTOS_MEMORIA_MAX)`, default **20000**, configurável por env.
3. Índice por veículo: `eventos_por_device: Dict[str, deque]` com `maxlen=EVENTOS_POR_DEVICE_MAX`, default **2000**. `get_recent_events(limit, device_id)` usa esse índice quando `device_id` é informado.
4. Formato dos eventos retornados **não muda**. Usado por `/api/fleet/events` e pelo App 2: `device_id`, `type`, `lat`, `lon`, `timestamp` (ISO string), `severity`, `icon` + campos extras.

**Critério de aceite:**
- Após 30 min de simulador, RSS do backend < 300 MB: `ps -o rss= -p <pid>`.
- `/api/fleet/events?limit=50&device_id=SIM-1008` responde em < 200 ms.

### T0.5 — Detecção de eventos por taxa real

**Problema:**
- `detect_events` compara a posição atual com `list(history)[-3]` (aceleração/frenagem) e `[-5]` (curva), ou seja, **quantidade de amostras**, apesar dos comentários "em 3 segundos". Com amostras a cada 5 s (simulador) ou 30–60 s (rastreadores reais), os limites não têm significado físico.
- `speeding` dispara **em toda amostra** acima de 80 km/h, inflando a contagem.

**Decisões:**
- Taxas calculadas entre **amostras consecutivas** do mesmo veículo:
  - `dt = (t_atual − t_anterior).total_seconds()`
  - ignorar o par se `dt < MIN_DT_S` (1) ou `dt > MAX_DT_S` (30)
- Limites (env, com defaults):

| Evento | Regra | medium | high | critical |
|---|---|---|---|---|
| `harsh_accel` | `a = (v−v_ant)/dt` km/h/s | a ≥ **8.0** (~0,23 g) | a ≥ 11.0 | a ≥ 14.0 |
| `harsh_brake` | `d = (v_ant−v)/dt` km/h/s | d ≥ **10.0** (~0,28 g) | d ≥ 13.0 | d ≥ 18.0 |
| `sharp_turn` | `r = Δrumo/dt` °/s, com `Δrumo = min(|h−h_ant|, 360−|h−h_ant|)` e `v ≥ 30` | r ≥ **15** | r ≥ 25 | r ≥ 40 |
| `speeding` | `v > 80` km/h. **1 evento por episódio**; o episódio termina quando `v < 75` | v > 80 | v ≥ 100 | v ≥ 120 |

- Campos extras preservados, para compatibilidade com o mapa do App 2:
  - `harsh_*`: `speed_before`, `speed_after`, `delta`, `acceleration_ms2` (= taxa/3,6), `dt_s`
  - `sharp_turn`: `heading_before`, `heading_after`, `heading_change`, `speed`, `dt_s`
  - `speeding`: `speed`, `speed_limit`, `excess`
  - `icon` igual ao atual (`⚡`, `🛑`, `🚨`, `↪️`; confira os emojis atuais no código).
- Estado do episódio de `speeding` por veículo em `vehicle_state[device_id]['speeding_ativo']`, sob o lock.
- Extrair a detecção para uma **função pura** `detectar_eventos(device_id, anterior, atual, estado) -> List[Dict]`, sem I/O, para permitir teste unitário. `add_position` orquestra.

**Limitação a documentar no código:** rastreadores reais com intervalo > 30 s não geram eventos de aceleração, frenagem ou curva, porque os pares são ignorados. Isso é intencional: sem granularidade não há como afirmar brusquidão.

**Critério de aceite:** testes de T0.10 passando.

### T0.6 — Score por janela deslizante

**Problema:** `update_score` só subtrai (inicial 85, piso 10) e nunca recupera.

**Decisão:** o score é calculado sobre os eventos **da janela** e não é mais acumulado. Uma função **pura**, compartilhada com o motor de monitores (T1.2):
```python
PESOS_EVENTO = {'harsh_brake': 3.0, 'harsh_accel': 2.0, 'sharp_turn': 2.0, 'speeding': 1.0}
MULT_SEVERIDADE = {'low': 0.5, 'medium': 1.0, 'high': 1.5, 'critical': 2.0}
SCORE_JANELA_MIN = 60     # env
SCORE_FATOR = 1.0         # env; calibrado em T0.11

def calcular_score(eventos: Iterable[dict], janela_minutos: float, fator: float = SCORE_FATOR) -> float:
    """eventos: dicts com 'type' (ou 'tipo') e 'severity' (ou 'severidade').
    Tipos fora de PESOS_EVENTO não afetam o score."""
    penalidade = sum(PESOS_EVENTO.get(tipo, 0) * MULT_SEVERIDADE.get(sev, 1.0) for ...)
    taxa_hora = penalidade * 60.0 / max(janela_minutos, 1)
    return round(max(0.0, min(100.0, 100.0 - fator * taxa_hora)), 1)
```
- `get_vehicle_score(device_id)` = `calcular_score(eventos do device com timestamp ≥ agora − SCORE_JANELA_MIN, SCORE_JANELA_MIN)`, usando o índice em memória de T0.4.
- Veículo sem eventos na janela = **100.0**.
- Veículo nunca visto: `get_vehicle_score` retorna **100.0**. `get_all_scores()` lista apenas veículos que enviaram posição desde o start.
- `get_fleet_stats()` mantém as chaves `fleet_avg`, `total_vehicles`, `events_today`, `top3`, `bottom3`. `events_today` muda em T0.8.
- Remover `update_score` e `INITIAL_SCORE`, ou manter só como alias documentado.

**Critério de aceite:** testes de T0.10. Em produção: um veículo cujos eventos saíram da janela volta a 100.

### T0.7 — Persistência de eventos eficiente e assíncrona

**Problema:** `save_event_to_db` abre **uma conexão nova por evento**, consulta `tipo_evento` e `veiculos` a cada evento e roda **síncrona** dentro da thread do socket.

**O que fazer:**
1. Caches em memória, com lock:
   - `codigo → tipo_evento_id`, recarregado a cada 10 min;
   - `device_id → veicod`, com consulta ao banco só no *miss*.
2. Fila `queue.Queue(maxsize=50000)` + **1 thread escritora** daemon, iniciada na primeira chamada. Ela junta eventos por até 1 s ou 500 itens e faz `executemany` numa conexão do pool (`db_config.tracker_conn()`).
3. `add_position` apenas enfileira. Se a fila estiver cheia, descarta, conta em `eventos_descartados` e loga um aviso a cada 60 s.
4. Evento sem `veicod` (FK NOT NULL) não é enfileirado. Registrar com contador.
5. Expor `GET /api/fleet/health` → `{fila_eventos, eventos_descartados, eventos_gravados_total}`.

**Critério de aceite:**
- Com simulador rodando, `/api/fleet/health.fila_eventos` fica < 100.
- `eventos_descartados` = 0.
- Novos eventos aparecem em `tracker.eventos` em ≤ 5 s.

### T0.8 — Consultas de eventos rápidas e "eventos hoje" real

**Problema:**
- `/api/events` (18,8 s) e `/api/events/stats` (15,7 s) usam `DATE(e.timestamp) = CURDATE()`, que não usa índice. Também tentam ler a memória antes do banco.
- `events_today` conta desde o start do processo.

**O que fazer:**
1. **Migration `005_indices_eventos.sql`:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_eventos_device_ts ON tracker.eventos (device_id, `timestamp`);
   CREATE INDEX IF NOT EXISTS idx_eventos_ts_tipo  ON tracker.eventos (`timestamp`, tipo_evento_id);
   ```
   A tabela tem ~2,6 mi linhas; pode levar alguns minutos. Registre o tempo no progresso.
2. `/api/events/stats`: **só banco**, com intervalo `e.timestamp >= CURDATE() AND e.timestamp < CURDATE() + INTERVAL 1 DAY`. Resposta:
   ```json
   {"total_eventos_hoje": 0, "por_categoria": {}, "por_tipo": {},
    "criticos": 0, "comportamentais": 0, "operacionais": 0,
    "eventos_por_hora": [{"hora": "08:00", "total": 0}], "top_tipos": [{"tipo": "harsh_brake", "count": 0}]}
   ```
   - `criticos`, `comportamentais` e `operacionais` vêm de `por_categoria`.
   - `eventos_por_hora` usa `GROUP BY HOUR(timestamp)` e inclui só horas com eventos.
   - Cache de 30 s em memória.
3. `/api/events`:
   - Novos parâmetros `desde` e `ate` (ISO; default: últimas 24 h) e `monitor_id` (filtra veículos ativos do monitor via `JOIN tracker.veiculomonitor vm ON vm.device_id = e.device_id AND vm.monitor_id = %s AND vm.ativo = 1`).
   - Manter `limit` (máx. 500), `device_id` e `categoria`. `ORDER BY e.timestamp DESC`.
   - Resposta mantém os campos atuais: `id`, `tipo_evento_codigo`, `tipo_evento_nome`, `categoria`, `severidade`, `device_id`, `timestamp`, `latitude`, `longitude`, `velocidade`, `dados_adicionais` (objeto) + `processado` (bool).
4. `get_fleet_stats().events_today` = `COUNT(*)` de hoje no banco (intervalo), com cache de 30 s.
5. `/api/monitors/<id>/vehicles`: `total_eventos_hoje` por veículo = `COUNT(*)` do dia por `device_id` (usa `idx_eventos_device_ts`), numa única consulta com `GROUP BY device_id` para todos os veículos do monitor.

**Critério de aceite** (mediana de 3 chamadas com `curl -w '%{time_total}'`):

| Endpoint | Tempo |
|---|---|
| `/api/events?limit=100` | < 2 s |
| `/api/events?device_id=SIM-1008&limit=100` | < 1 s |
| `/api/events?monitor_id=4&limit=100` | < 2 s |
| `/api/events/stats` | < 2 s na 1ª chamada; < 50 ms com cache |
| `/api/monitors/4/vehicles` | < 1,5 s |

Além disso, `events_today` de `/api/fleet/stats` bate com `SELECT COUNT(*)` do dia (±1 ciclo).

### T0.9 — Simulador realista

**Problema:** `aitrackdatadrivr/simulator.py` tem perfis de velocidade, mas:
- (a) o **rumo é sorteado** a cada pacote (`heading = random.uniform(0, 359)`), o que gera curvas falsas;
- (b) as variações do perfil "poor" (máx. 28 km/h em 5 s ≈ 5,6 km/h/s) **não atingem** os novos limites realistas;
- (c) a documentação manda usar o `simulator.py` da raiz, que sorteia tudo.

**O que fazer:**
1. **Rumo:** calcular o azimute entre o ponto anterior e o atual da rota:
   `atan2(sin Δλ·cos φ2, cos φ1·sin φ2 − sin φ1·cos φ2·cos Δλ)`, convertido para 0–360°.
   Se os pontos forem iguais, manter o rumo anterior.
2. **Velocidade por perfil**, a cada tick de 5 s (720 ticks/h):

   | Perfil | Variação normal | Prob. de evento brusco por tick | Evento brusco | Velocidade máx. |
   |---|---|---|---|---|
   | good | ±3 | 0,001 (~0,7/h) | ±(50–65) km/h no tick | 75 |
   | moderate | ±6 | 0,008 (~6/h) | ±(50–65) | 90 |
   | poor | ±10 | 0,03 (~22/h) | ±(50–65) | 115 |

   - Evento brusco: se a velocidade atual ≥ 50, sorteia frear ou acelerar; se < 50, só acelera.
   - Limite inferior da velocidade: 0.
   - Após atingir a velocidade máxima, volta a variar normalmente.
3. Parâmetros por linha de comando: `--intervalo` (default 5), `--veiculos` (default 10), `--host`, `--porta`.
4. Adicionar no topo do `simulator.py` **da raiz**: `# LEGADO — não use. Use aitrackdatadrivr/simulator.py (perfis realistas).`
5. Atualizar `comorodartudo.md` (raiz) e `aitrackdatadrivr/COMO_RODAR.md`:
   - simulador = `aitrackdatadrivr/simulator.py`;
   - App 2 na porta 3003;
   - uso do venv.

**Critério de aceite:** coberto por T0.11.

### T0.10 — Testes unitários do motor comportamental

**O que fazer:** criar `aitrackdatadrivr/tests/` com `conftest.py`, que insere `aitrackdatadrivr/` no `sys.path` e aplica monkeypatch global para que **nada grave no banco**. Criar `tests/test_behavioral_engine.py` com, no mínimo:
1. Velocidade suave (40 → 42 km/h em 5 s) → nenhum evento.
2. 20 → 70 km/h em 5 s (10 km/h/s) → 1 `harsh_accel` `medium`.
3. 80 → 20 km/h em 5 s (12 km/h/s) → 1 `harsh_brake` `medium`. 90 → 0 em 5 s (18 km/h/s) → `critical`.
4. Par com `dt = 40 s` → nenhum evento.
5. Rumo 0° → 100° em 5 s a 50 km/h (20°/s) → `sharp_turn` `medium`. Mesmo giro a 20 km/h → nenhum. Rumo 350° → 10° (Δ = 20°) em 1 s a 50 km/h → `sharp_turn` (testa a volta dos 360°).
6. Sequência 70, 85, 90, 88, 85, 74, 82 km/h (amostras a cada 5 s) → **2** eventos `speeding` (dois episódios) e nenhum `harsh_*`.
7. `calcular_score([], 60)` = 100. Com 10 `harsh_brake` `high` em 60 min e fator 1 → `100 − 45 = 55`.
8. Evento com timestamp mais antigo que a janela **não** afeta `get_vehicle_score`.
9. `vehicle_events` não passa de `EVENTOS_MEMORIA_MAX`.

Também tornar executável: `cd aitrackdatadrivr && .venv/bin/python -m pytest -q tests`. Atualizar `AGENTS.md` §3.6.

**Critério de aceite:** todos os testes passando e nenhuma linha nova em `tracker.eventos` durante a execução.

### T0.11 — Calibração e validação da Fase 0 (sem commit de código, só registro)

**O que fazer:**
1. Reiniciar o backend (zera a memória) e rodar `aitrackdatadrivr/simulator.py` por **30 minutos**.
2. Coletar `/api/fleet/scores` a cada 5 min e calcular a média por perfil.
3. Critérios, a partir de 20 min de execução:

   | Grupo | Veículos | Critério |
   |---|---|---|
   | good | SIM-1000..1004 | média **≥ 85** |
   | moderate | SIM-1005..1007 | média **entre 55 e 85** |
   | poor | SIM-1008..1009 | média **< 55** |

4. Se não bater, ajuste **nesta ordem**: `SCORE_FATOR` (env), depois as probabilidades do simulador. **Não mude os limites de detecção de T0.5.**
5. Registrar na seção 10 os valores finais de `SCORE_FATOR` e das probabilidades, as médias obtidas e o RSS do processo.

**Critério de aceite da Fase 0 inteira:**
- As três faixas acima atendidas.
- Tempos de T0.8 atendidos.
- RSS < 300 MB.
- App 1 funcionando.
- Testes passando.

---

## 5. FASE 1 — Ligar o motor de monitores (regras)

### T1.1 — Migration de configuração e limpeza do seed de alertas

**Migration `006_monitor_cooldown.sql`:**
```sql
ALTER TABLE tracker.monitores
  ADD COLUMN IF NOT EXISTS cooldown_alerta_min INT NOT NULL DEFAULT 60;
```
**Migration `007_remove_alertas_mock.sql`:** faça **backup antes** com `mysqldump` da tabela `monitor_alertas` (ver `AGENTS.md` §4).
```sql
-- Remove os 4 alertas falsos inseridos por 004_seed_mock_alerts.sql (27/02/2026, sem análise)
DELETE FROM tracker.monitor_alertas
 WHERE analise_id IS NULL AND criado_em < '2026-03-01 00:00:00';
```
**Critério de aceite:** `SELECT COUNT(*) FROM tracker.monitor_alertas` = 0 e coluna `cooldown_alerta_min` existe.

### T1.2 — `analyze_monitor` lendo do banco

**Problema:** hoje `analyze_monitor` lê score e eventos da memória: some ao reiniciar e depende do processo. Usa score acumulado (inútil), `score_inicial = score + 5` (inventado) e não evita reanalisar quando nada mudou.

**O que fazer** (reescrever `server/monitor_engine.py`; manter `monitor_db.save_analysis` e `create_alert`, ampliando-os se preciso):
```
analyze_monitor(monitor_id, forcar=False) -> dict {analises:[...], alertas:[...], ignorados:[{device_id, motivo}]}
  monitor = monitor_db.get_monitor_by_id(monitor_id); se inativo e não forcar → retorna vazio
  janela_min = monitor.janela_contexto / 60
  fim = agora; inicio = fim − janela
  veiculos = monitor_db.get_monitor_vehicles(monitor_id)  (só ativos)
  para cada veículo:
     eventos = monitor_db.get_eventos_janela(device_id, inicio, fim)
         # SELECT te.codigo AS tipo, te.categoria, e.severidade, e.timestamp, e.velocidade,
         #        e.latitude, e.longitude, e.dados_adicionais
         # FROM tracker.eventos e JOIN tracker.tipo_evento te ON te.id = e.tipo_evento_id
         # WHERE e.device_id = %s AND e.timestamp >= %s AND e.timestamp < %s
         # ORDER BY e.timestamp
     score = behavioral_engine.calcular_score(eventos, janela_min)
     ultima = monitor_db.get_ultima_analise(veiculomonitor_id)       # nova função
     SE não forcar:
        se score >= monitor.score_threshold → ignora ("score_ok")
        se len(eventos) < monitor.eventos_minimos → ignora ("poucos_eventos")
        se ultima e não existe evento com timestamp > ultima.periodo_fim → ignora ("sem_eventos_novos")
     resultado = analisar_por_regras(monitor, veiculo, eventos, score)   # Fase 2 troca por LLM com fallback
     analise_id = monitor_db.save_analysis(..., score_inicial = ultima.score_final se existir senão NULL,
                                           score_final = score, periodo_inicio=inicio, periodo_fim=fim, ...)
     avaliar_alerta(monitor, veiculo, resultado, analise_id)            # T1.4
```
- `analisar_por_regras`:
  - severidade: `critical` se score < 40; `high` se < 55; senão `medium`;
  - conclusão: `"Score {score:.1f} na janela de {janela_min:.0f} min — {n} eventos. Mais frequentes: tipo (n), …"`;
  - `gerar_alerta = severidade in ('high','critical')`.
- O parâmetro `forcar=True` (usado pelo endpoint de T1.5) ignora os três filtros, mas continua respeitando o cooldown de alerta.

### T1.3 — Loop do motor dentro do backend

**O que fazer:**
1. Remover o uso de `schedule`. Novo loop em `monitor_engine`:
   ```
   start_in_background() -> Thread daemon "monitor-engine" (idempotente; só inicia uma vez)
   _loop():
      proxima = {}   # monitor_id -> datetime
      a cada 10 s:
         a cada 60 s: monitores = monitor_db.get_active_monitors()   # recarrega (pega criação/edição/toggle)
         para cada monitor ativo cuja proxima execução venceu (ou nunca rodou):
             executa analyze_monitor(id) sob _lock_por_monitor[id] (não bloqueante: se ocupado, pula)
             proxima[id] = agora + intervalo_analise
         exceções: log e segue (o loop nunca morre)
   ```
2. `run.py`: iniciar `monitor_engine.start_in_background()` após a API e monitorar a thread como as demais. Variável `MONITOR_ENGINE_HABILITADO` (env, default `1`) permite desligar.
3. Logging com `logging.getLogger("monitor_engine")`: início de ciclo, veículos analisados e ignorados com motivo, alertas criados e duração.

**Critério de aceite:**
- Log mostra ciclos a cada ≤ intervalo de cada monitor.
- Desativar um monitor via `POST /api/monitors/<id>/toggle` faz o motor parar de analisá-lo em ≤ 70 s, sem reiniciar.

### T1.4 — Regras de alerta sem duplicatas

**Decisão:**
```
avaliar_alerta(monitor, veiculo, resultado, analise_id):
   se não monitor.gera_alertas ou not resultado.gerar_alerta ou resultado.severidade not in ('high','critical'): return
   aberto = SELECT ... FROM tracker.monitor_alertas
            WHERE monitor_id=%s AND veiculomonitor_id=%s AND status IN ('pending','acknowledged')
              AND criado_em >= NOW() - INTERVAL cooldown_alerta_min MINUTE
            ORDER BY criado_em DESC LIMIT 1
   se aberto existe:
       se ordem(resultado.severidade) > ordem(aberto.severidade):  # escalonamento high → critical
           cria alerta novo
       senão: não cria (log "alerta suprimido por cooldown")
   senão: cria alerta
```
- Mapeamento `monitores.tipo_monitor` → `monitor_alertas.tipo`: `safety→safety`, `efficiency→efficiency`, `compliance→compliance`, `predictive→prediction`, `custom→behavior`.
- `titulo`: `"Risco {severidade}: {device_id} com score {score:.1f}"` (regras; a Fase 2 usa o título do LLM).
- `mensagem` = conclusão.
- `total_eventos_relacionados` = nº de eventos da janela.

### T1.5 — Endpoints de operação do motor

- `POST /api/monitors/<id>/analyze` → executa `analyze_monitor(id, forcar=True)` de forma síncrona e retorna o dict de T1.2 com as análises e alertas criados, já serializados. Timeout do Flask não é problema em dev. Documentar no Apêndice A.
- `GET /api/monitors/engine/status` → `{habilitado, rodando, ultimo_ciclo_em, proximas_execucoes: {monitor_id: iso}, analises_ultima_hora, alertas_ultima_hora}`.
- `GET /api/monitors/<id>/analyses` já existe. Garantir `limit` via query string (default 50, máx. 200).

### T1.6 — Testes e validação da Fase 1

1. Testes unitários `aitrackdatadrivr/tests/test_monitor_engine.py`, com `monitor_db` falso em memória:
   - score ≥ limite → ignorado;
   - sem eventos novos → ignorado;
   - severidade `high` → alerta;
   - segundo `high` dentro do cooldown → suprimido;
   - `critical` após `high` aberto → cria (escalonamento);
   - `forcar=True` analisa mesmo com score ok.
2. Validação real de 30 min (backend + simulador):
   - `SELECT COUNT(*) FROM tracker.monitor_analises` > 0.
   - Alertas `pending`: esperados **principalmente** para `SIM-1008`, no monitor #4, o único monitor ativo com veículo `poor`. `SIM-1009` está no monitor #5, inativo.
   - Alertas dos `moderate` (`SIM-1005..1007`) são aceitáveis só se esporádicos: **≤ 2 em 30 min** no total.
   - Nenhum par `(monitor_id, veiculomonitor_id)` com mais de 1 alerta `pending` da mesma severidade em 60 min:
     ```sql
     SELECT monitor_id, veiculomonitor_id, severidade, COUNT(*) FROM tracker.monitor_alertas
     WHERE status='pending' AND criado_em >= NOW() - INTERVAL 60 MINUTE
     GROUP BY 1,2,3 HAVING COUNT(*) > 1;   -- deve retornar vazio
     ```
   - Veículos `good` sem alertas.
   - Registrar na seção 10 as contagens de análises e alertas por monitor.

---

## 6. FASE 2 — Análise com Claude (LLM)

**Decisões gerais:**
- SDK oficial `anthropic` (≥ 1.6.0, no venv). Modelo padrão **`claude-opus-5`**, configurável por monitor. Use exatamente esse ID, sem sufixo de data.
- Saída **estruturada** (JSON validado por schema) via `output_config.format`.
- Fallback de recusa **no servidor** habilitado: beta `server-side-fallback-2026-07-01` com `fallbacks="default"`.
- **As regras continuam como pré-filtro.** O LLM só é chamado quando a Fase 1 decidiria analisar. Em qualquer falha do LLM, usa-se a análise por regras e o erro é gravado. O motor nunca para por causa do LLM.
- Sem limite de custo definido pelo usuário. O pré-filtro e a regra de "sem eventos novos" evitam chamadas inúteis.

### T2.1 — Configuração

Em `config/.env` (e chaves vazias em `.env.example`):
```
ANTHROPIC_API_KEY=            # fornecida pelo usuário; NUNCA commitar
LLM_HABILITADO=1
LLM_MODELO_PADRAO=claude-opus-5
LLM_TIMEOUT_S=120
LLM_MAX_RETRIES=2
LLM_MAX_EVENTOS_CONTEXTO=60
```
Se `ANTHROPIC_API_KEY` estiver vazia, o motor loga **uma vez** `"LLM desabilitado: ANTHROPIC_API_KEY ausente — usando regras"` e segue só com regras. Isso não é erro. Se não houver chave disponível, **peça ao usuário** e registre na seção 10. Enquanto isso, implemente e teste com o cliente simulado (T2.6).

### T2.2 — Migration `008_monitor_llm.sql`

```sql
ALTER TABLE tracker.monitores
  ADD COLUMN IF NOT EXISTS usa_llm TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS modelo_llm VARCHAR(50) NOT NULL DEFAULT 'claude-opus-5',
  ADD COLUMN IF NOT EXISTS instrucoes_llm TEXT NULL;

ALTER TABLE tracker.monitor_analises
  ADD COLUMN IF NOT EXISTS origem ENUM('regras','llm') NOT NULL DEFAULT 'regras',
  ADD COLUMN IF NOT EXISTS titulo VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS resumo TEXT NULL,
  ADD COLUMN IF NOT EXISTS padroes LONGTEXT NULL,        -- JSON: lista de strings
  ADD COLUMN IF NOT EXISTS recomendacoes LONGTEXT NULL,  -- JSON: lista de strings
  ADD COLUMN IF NOT EXISTS confianca FLOAT NULL,
  ADD COLUMN IF NOT EXISTS modelo VARCHAR(50) NULL,      -- modelo que efetivamente respondeu (response.model)
  ADD COLUMN IF NOT EXISTS tokens_entrada INT NULL,
  ADD COLUMN IF NOT EXISTS tokens_saida INT NULL,
  ADD COLUMN IF NOT EXISTS tempo_ms INT NULL,
  ADD COLUMN IF NOT EXISTS request_id VARCHAR(100) NULL,
  ADD COLUMN IF NOT EXISTS erro_llm TEXT NULL;
```
Atualizar `monitor_db`:
- `get_monitor_by_id`, `get_all_monitors` e `get_active_monitors` retornam os novos campos;
- `create_monitor` e `update_monitor` aceitam `cooldown_alerta_min`, `usa_llm`, `modelo_llm` e `instrucoes_llm`;
- `save_analysis` grava os novos campos, com listas serializadas em JSON;
- `get_monitor_analyses` desserializa `padroes` e `recomendacoes`.

### T2.3 — `server/llm_client.py`

**Modelo de saída** (pydantic v2):
```python
from typing import Literal
from pydantic import BaseModel

class ResultadoAnalise(BaseModel):
    severidade: Literal['low', 'medium', 'high', 'critical']
    gerar_alerta: bool
    titulo: str             # até 120 caracteres (truncar no código se vier maior)
    resumo: str             # até 800 caracteres (truncar no código)
    padroes: list[str]      # 0 a 5 itens (cortar no código)
    recomendacoes: list[str]  # 1 a 5 itens (cortar no código)
    confianca: float        # 0.0 a 1.0 (limitar no código)
```

**JSON Schema** enviado à API:
```json
{"type": "object",
 "properties": {
   "severidade": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
   "gerar_alerta": {"type": "boolean"},
   "titulo": {"type": "string"},
   "resumo": {"type": "string"},
   "padroes": {"type": "array", "items": {"type": "string"}},
   "recomendacoes": {"type": "array", "items": {"type": "string"}},
   "confianca": {"type": "number"}},
 "required": ["severidade", "gerar_alerta", "titulo", "resumo", "padroes", "recomendacoes", "confianca"],
 "additionalProperties": false}
```
Não use `maxLength`, `minItems` ou `maxItems` no schema. Limite pelo prompt e valide ou trunque no código.

**Prompt de sistema** (constante `SYSTEM_PROMPT`, texto fixo, sem data ou hora dentro dele):
```
Você é um analista sênior de segurança e comportamento de motoristas de frotas.
Recebe, em JSON, os eventos de condução de UM veículo numa janela de tempo, o score comportamental
(0–100, onde 100 é ideal) e a configuração do monitor que pediu a análise.

Sua tarefa:
1. Identificar padrões de risco reais nos dados (frequência, concentração no tempo, combinação de
   eventos, velocidades envolvidas, piora em relação à análise anterior).
2. Classificar a severidade:
   - low: comportamento aceitável, eventos isolados;
   - medium: atenção, padrão incipiente;
   - high: padrão consistente de risco que justifica contato com o motorista;
   - critical: risco iminente de acidente ou comportamento gravíssimo e reiterado.
3. Decidir se deve gerar alerta para o gestor (gerar_alerta=true apenas para high ou critical com
   evidência clara nos dados).
4. Escrever título curto (até 120 caracteres), resumo objetivo (até 800 caracteres), até 5 padrões
   observados e de 1 a 5 recomendações práticas e acionáveis para o gestor da frota.
5. Informar sua confiança (0 a 1) com base na quantidade e qualidade dos dados.

Regras:
- Responda em português do Brasil.
- Use somente os dados fornecidos. Não invente eventos, locais, nomes ou números.
- Se os dados forem insuficientes, diga isso no resumo e use confiança baixa.
- Considere as instruções específicas do monitor, se houver, sem violar as regras acima.
```

**Contexto enviado como mensagem do usuário** (`json.dumps(contexto, ensure_ascii=False, default=str)`):
```json
{
  "monitor": {"id": 4, "nome": "Monitor #4", "tipo": "safety", "janela_minutos": 30,
              "score_limite": 65, "instrucoes": null},
  "veiculo": {"device_id": "SIM-1008", "placa": "SIM-1008", "tipo": "tracker", "motorista": null},
  "periodo": {"inicio": "2026-09-16T14:00:00", "fim": "2026-09-16T14:30:00"},
  "score": {"atual": 41.5, "anterior": 58.0},
  "resumo_eventos": {"total": 23,
                     "por_tipo": {"harsh_brake": 9, "harsh_accel": 8, "speeding": 4, "sharp_turn": 2},
                     "por_severidade": {"medium": 14, "high": 7, "critical": 2}},
  "velocidade_nos_eventos": {"max_kmh": 112.0, "media_kmh": 63.4},
  "eventos": [{"hora": "14:02:11", "tipo": "harsh_brake", "severidade": "high", "kmh": 58.0,
               "detalhe": {"delta": 62.0, "dt_s": 5.0}}],
  "analise_anterior": {"quando": "2026-09-16T13:55:00", "severidade": "high",
                       "resumo": "…"}
}
```
- `eventos`: os `LLM_MAX_EVENTOS_CONTEXTO` mais recentes da janela, em ordem cronológica.
- `detalhe`: só os campos numéricos úteis de `dados_adicionais` (`delta`, `dt_s`, `heading_change`, `excess`).
- `analise_anterior`: `null` quando não houver.

**Chamada:**
```python
import anthropic

_client = None
def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=LLM_TIMEOUT_S, max_retries=LLM_MAX_RETRIES)  # lê ANTHROPIC_API_KEY
    return _client

def analisar(contexto: dict, modelo: str, instrucoes: str | None) -> tuple[ResultadoAnalise | None, dict]:
    """Retorna (resultado, meta). meta = {modelo, tokens_entrada, tokens_saida, tempo_ms, request_id, erro}.
    Nunca levanta exceção: em falha, resultado=None e meta['erro'] preenchido."""
    inicio = time.monotonic()
    try:
        resp = _get_client().beta.messages.create(
            model=modelo,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(contexto, ensure_ascii=False, default=str)}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if resp.stop_reason == "refusal":   -> erro "recusa: {resp.stop_details.category if resp.stop_details else ''}"
        if resp.stop_reason == "max_tokens": -> erro "resposta truncada"
        texto = next(b.text for b in resp.content if b.type == "text")
        resultado = ResultadoAnalise.model_validate_json(texto)   # depois truncar/limitar campos
        meta = {modelo: resp.model, tokens_entrada: resp.usage.input_tokens,
                tokens_saida: resp.usage.output_tokens, request_id: resp._request_id, ...}
    except anthropic.AuthenticationError / PermissionDeniedError / NotFoundError / BadRequestError: erro (não repetir)
    except anthropic.RateLimitError / APIStatusError / APIConnectionError / APITimeoutError: erro (o SDK já fez retries)
    except pydantic.ValidationError / StopIteration / json errors: erro "resposta inválida"
```
Observações:
- **Não** envie `temperature`, `top_p` ou `thinking={"type": "enabled", "budget_tokens": ...}`: são rejeitados no `claude-opus-5`. O thinking adaptativo já é o padrão desse modelo; não configure nada.
- **Não** faça *prefill* de mensagem do assistente (retorna 400).
- Se, na versão instalada do SDK, `client.beta.messages.create` não aceitar `fallbacks` ou `output_config`:
  1. Consulte `https://docs.claude.com` (Structured outputs / refusal fallbacks) e o repositório `anthropics/anthropic-sdk-python`.
  2. Se ainda assim não funcionar, use `client.messages.create` com `output_config` e **sem** `betas`/`fallbacks`.
  3. Registre a decisão na seção 10.
  **Não** troque para outro provedor nem para HTTP cru.
- O prompt de sistema é pequeno (< 1 k tokens). Não é necessário configurar cache de prompt.

### T2.4 — Integração no motor

Em `analyze_monitor` (T1.2), trocar `analisar_por_regras` por:
```
regras = analisar_por_regras(...)                      # sempre calculado (fallback e referência)
se LLM_HABILITADO e ANTHROPIC_API_KEY e monitor.usa_llm:
    contexto = montar_contexto(monitor, veiculo, eventos, score, ultima)
    resultado, meta = llm_client.analisar(contexto, monitor.modelo_llm, monitor.instrucoes_llm)
    se resultado: origem='llm'; usa resultado (severidade, gerar_alerta, titulo, resumo, padroes, recomendacoes, confianca)
    senão:        origem='regras'; usa regras; grava meta.erro em erro_llm
senão: origem='regras'
save_analysis(... origem, titulo, resumo (regras: a conclusão), padroes, recomendacoes, confianca, modelo, tokens..., erro_llm)
conclusao = resumo (manter a coluna antiga preenchida para compatibilidade)
avaliar_alerta(...)  → titulo do alerta = resultado.titulo; mensagem = resultado.resumo
```
- Chamadas ao LLM ocorrem na thread do motor, **sequencialmente**. Se um ciclo demorar mais que o intervalo, o próximo simplesmente atrasa. O lock por monitor de T1.3 impede sobreposição.

### T2.5 — API expondo os dados da IA

- `GET /api/monitors/<id>/analyses`: inclui `origem`, `titulo`, `resumo`, `padroes` (lista), `recomendacoes` (lista), `confianca`, `modelo`, `tokens_entrada`, `tokens_saida`, `tempo_ms`, `erro_llm` e `device_id`.
- `GET /api/alerts` (`monitor_db.get_alerts`):
  - `LEFT JOIN tracker.monitores m ON m.id = a.monitor_id` → `monitor_nome`;
  - `LEFT JOIN tracker.monitor_analises an ON an.id = a.analise_id` → `analise_origem`, `analise_resumo`, `recomendacoes` (lista), `padroes` (lista), `confianca`, `modelo`;
  - novos filtros `device_id` e `limit` (default 100, máx. 500).
- `GET /api/monitors/engine/status` (T1.5): acrescentar `llm_habilitado`, `modelo_padrao`, `chamadas_llm_ultima_hora`, `falhas_llm_ultima_hora` e `tokens_ultima_hora` (entrada/saída).

### T2.6 — Testes e validação da Fase 2

1. `tests/test_llm_client.py` com cliente **falso** (monkeypatch de `_get_client`), sem rede:
   - resposta válida → `ResultadoAnalise` e meta com tokens;
   - `stop_reason="refusal"` → `resultado=None`, erro contendo "recusa";
   - JSON inválido → erro "resposta inválida";
   - exceção `APIConnectionError` → erro, sem levantar;
   - campos longos são truncados (título > 120).
2. `tests/test_monitor_engine.py`: com LLM falso retornando `gerar_alerta=true, severidade=critical` → análise `origem='llm'` e alerta com o título do LLM. Com LLM falhando → `origem='regras'` e `erro_llm` preenchido.
3. `aitrackdatadrivr/scripts/smoke_llm.py`: **1 chamada real** com um contexto fixo de exemplo. Imprime o resultado validado, tokens e `request_id`. Só roda se a chave existir.
4. Validação real, com chave:
   - `POST /api/monitors/4/analyze` → análise de `SIM-1008` com `origem='llm'`, texto em português, `recomendacoes` não vazia e tokens > 0.
   - Deixar 30 min rodando: análises com `origem='llm'`, nenhum alerta duplicado (consulta de T1.6).
   - Forçar falha (`LLM_MODELO_PADRAO=modelo-inexistente` ou `modelo_llm` inválido num monitor) → análises seguem com `origem='regras'` e `erro_llm`, sem crash.
   - Registrar na seção 10 os tokens médios por análise e o tempo médio.

---

## 7. FASE 3 — Frontend real (App 2, sem mock)

Diretório: `aitrackdatadrivr/frontend/src`. Hoje:
- `AlertsPanel.tsx` usa `mockAlerts`/`mockAlertStats`, e os botões só chamam `alert(...)`;
- `MonitorDetailView.tsx` usa `mockEvents`;
- `App.tsx` injeta `mockVehiclesInMonitors`;
- `EventsCatalog.tsx` usa `eventTypesCatalog`/`mockEventStats`;
- `MonitorDashboard.tsx` importa **tipos** de `mockData/`.

`services/apiService.ts` já tem `monitorService`, `alertService`, `eventService`, `vehicleService` e `fleetService`; só `monitorService.getAll/getById/getVehicles` é usado.

**Regras desta fase:**
- Toda chamada HTTP passa por `apiService.ts`, incluindo as que hoje estão direto nos componentes, quando você mexer neles.
- Nenhum `window.alert`, `confirm` ou `prompt`. Use feedback inline (mensagem temporária no próprio painel).
- Estados de carregando, erro e vazio explícitos em cada painel.
- `npx tsc --noEmit` e `npm run build` sem erros a cada tarefa.

### T3.1 — Tipos reais em `src/types/`

Criar `src/types/monitor.ts`, `alert.ts`, `event.ts` e `fleet.ts`, espelhando **exatamente** as respostas da API após as Fases 0–2. Confira com `curl` antes de escrever.
- `Monitor`: `id`, `nome`, `descricao`, `tipo_monitor`, `ativo` (**number 0/1 na API**: converta para boolean num único lugar, no `apiService`), `intervalo_analise`, `janela_contexto`, `eventos_minimos`, `score_threshold`, `gera_alertas`, `cooldown_alerta_min`, `usa_llm`, `modelo_llm`, `instrucoes_llm`, `veiculos_monitorados`, `criado_em`, `atualizado_em`.
- `VeiculoMonitor`: `id`, `monitor_id`, `tipo_veiculo`, `device_id`, `placa`, `veicod_tracker`, `codusu_dirijabem`, `ativo`, `atribuido_em`, `score_atual` (number | null), `total_eventos_hoje`, `status` ('ok' | 'warning' | 'critical' | 'desconhecido').
- `Analise`: campos de T2.5.
- `Alerta`: `id`, `analise_id`, `monitor_id`, `monitor_nome`, `veiculomonitor_id`, `device_id`, `nome_motorista`, `titulo`, `mensagem`, `severidade`, `tipo`, `criado_em`, `status`, `reconhecido_em`, `reconhecido_por`, `total_eventos_relacionados`, `analise_origem`, `analise_resumo`, `recomendacoes`, `padroes`, `confianca`, `modelo`.
- `EstatisticasAlertas`: T3.2. `TipoEvento` e `Evento`: T0.8 e T3.5. `EstatisticasEventos`: T0.8.

Tipar os retornos do `apiService` (`axios.get<T>`).

### T3.2 — Aba Alertas real

**Backend primeiro** (`monitor_db.get_alert_stats` → `/api/alerts/stats`). Hoje devolve contagens como **string** (`"1"`). Passar a devolver **inteiros** e acrescentar campos:
```json
{"total": 0, "pending": 0, "acknowledged": 0, "resolved": 0, "dismissed": 0,
 "low": 0, "medium": 0, "high": 0, "critical": 0,
 "ativos": 0,
 "reconhecidos_hoje": 0, "resolvidos_hoje": 0,
 "taxa_resolucao_24h": null,
 "tempo_medio_reconhecimento_min": null}
```
- `ativos` = pending + acknowledged.
- `*_hoje` usam intervalo do dia sobre `reconhecido_em` e sobre a data de resolução. **Não existe coluna `resolvido_em`**: adicione `resolvido_em DATETIME NULL` na migration `009_alertas_resolucao.sql` e preencha-a em `resolve_alert`; `dismiss_alert` também grava nela.
- `taxa_resolucao_24h` = resolvidos nas últimas 24 h ÷ criados nas últimas 24 h, ou `null` se 0.
- `tempo_medio_reconhecimento_min` = média de `TIMESTAMPDIFF(SECOND, criado_em, reconhecido_em)/60` nos últimos 7 dias, ou `null`.

**Frontend** (`AlertsPanel.tsx` e subcomponentes `AlertsHeader`, `AlertsFilters`, `AlertsList`, `AlertDetails`):

| Mock usado hoje | Substituir por |
|---|---|
| `mockAlerts` | `alertService.getAll({status?, severidade?})`, polling a cada 10 s |
| `mockAlertStats.total_alertas_ativos` | `stats.ativos` |
| `criticos` / `altos` / `medios` / `baixos` | `critical` / `high` / `medium` / `low` |
| `reconhecidos_hoje`, `resolvidos_hoje`, `taxa_resolucao_24h`, `tempo_medio_reconhecimento_min` | mesmos nomes (tratar `null` como "—") |
| `alert.eventos_relacionados` | `total_eventos_relacionados` |
| `alert.llm_analise_resumo` | `analise_resumo` (se `null`, esconder o bloco) |
| `alert.recomendacoes` | `recomendacoes` (lista; pode estar vazia) |
| `alert.monitor_nome` | `monitor_nome` |
| `localizacao_lat/lon` (se usados) | remover da tela |

- Botões:
  - **Reconhecer** → `alertService.acknowledge(id, "operador")`
  - **Resolver** → `alertService.resolve(id)`
  - **Descartar** (novo) → `alertService.dismiss(id)`
  - Após cada ação: recarregar lista e estatísticas; mostrar mensagem inline de sucesso ou erro.
  - Mostrar só os botões válidos para o status: `pending` → Reconhecer, Resolver, Descartar; `acknowledged` → Resolver, Descartar; demais → nenhum.
- Badge de origem: "IA" quando `analise_origem='llm'`, "Regras" caso contrário.
- `reconhecido_por` fixo `"operador"`: **não há autenticação no sistema**. Registrar isso como limitação conhecida.

### T3.3 — Aba Monitores AI completa

Em `MonitorDashboard.tsx` (lista e detalhe na barra lateral):
1. **Status real dos veículos**, já corrigido em T0.3. Exibir `score_atual` (ou "—" se null) e cores por `status`.
2. **Últimas análises** do monitor selecionado:
   - `monitorService.getAnalyses(id, 20)`, polling de 30 s;
   - cada item mostra `analisado_em`, veículo, badge IA/Regras, severidade, `titulo`, `resumo` e `recomendacoes`;
   - em letra pequena: `modelo` · tokens · `tempo_ms`;
   - quando `erro_llm` existir: aviso "IA indisponível nesta análise".
3. **Analisar agora** → `POST /api/monitors/<id>/analyze` (adicionar `monitorService.analyzeNow`). Mostrar spinner, pois pode levar dezenas de segundos com LLM, e recarregar análises ao terminar.
4. **Ativar/desativar** → `monitorService.toggle(id, !ativo)`. Na lista, monitores inativos continuam clicáveis para edição.
5. **Criar e editar monitor:** formulário com `nome`, `descricao`, `tipo_monitor`, `intervalo_analise` (em minutos na tela, segundos na API), `janela_contexto` (min ↔ s), `eventos_minimos`, `score_threshold`, `gera_alertas`, `cooldown_alerta_min`, `usa_llm`, `modelo_llm` (texto, default `claude-opus-5`) e `instrucoes_llm` (textarea). Validação: números positivos; `janela_contexto` ≥ `intervalo_analise`. Confira `POST/PUT /api/monitors`; ajuste o backend se algum campo não for aceito.
6. **Veículos do monitor:**
   - adicionar a partir de `/api/vehicles/unified` (só `tracker_only`/`both` até T4.2) → `vehicleService.addToMonitor(monitorId, veicod, device_id)`.
   - `/api/vehicles/unified` **não** retorna `veicod`. Resolva no backend: `POST /api/monitors/<id>/vehicles` aceita `{device_id}` e busca o `VEICOD` em `tracker.veiculos` pelo `VEI_DEVICE_ID`.
   - remover → `vehicleService.removeFromMonitor(veiculomonitorId)`.
7. Ao selecionar um veículo, mantém o comportamento atual (`onVehicleSelect`).

### T3.4 — Painel de detalhe do monitor real

- `App.tsx`: remover `mockVehiclesInMonitors` e o import de `mockData`. `MonitorDetailView` recebe só `monitorId` e `selectedVehicle` e **busca** os veículos com `monitorService.getVehicles(monitorId)`.
- Eventos:
  - com veículo selecionado: `eventService.getAll({device_id, limit: 100, desde: agora − 24 h})`;
  - sem veículo: `eventService.getAll({monitor_id, limit: 200, desde: agora − 24 h})` (parâmetros de T0.8);
  - polling de 15 s;
  - campos: `tipo_evento_codigo`, `tipo_evento_nome`, `categoria`, `severidade`, `device_id`, `timestamp`, `latitude`, `longitude`, `velocidade`.
- Ícones: criar `src/utils/eventIcons.ts` com o mapa `codigo → emoji`, copiando os emojis de `mockData/mockEvents.ts` (`eventTypesCatalog`) **antes** de apagar a pasta. O campo `icone` do banco é texto (`'accel'`) e não deve ser exibido.
- Mantém a organização atual por categoria (critical / behavioral / operational).

### T3.5 — Catálogo de eventos real

**Migration `010_catalogo_eventos.sql`:**
```sql
ALTER TABLE tracker.tipo_evento
  ADD COLUMN IF NOT EXISTS tempo_resposta_segundos INT NULL,
  ADD COLUMN IF NOT EXISTS deteccao_ativa TINYINT(1) NOT NULL DEFAULT 0;
UPDATE tracker.tipo_evento SET deteccao_ativa = 1
 WHERE codigo IN ('harsh_brake','harsh_accel','speeding','sharp_turn');
INSERT IGNORE INTO tracker.tipo_evento (codigo, nome, categoria, severidade_padrao, icone, cor, descricao, tempo_resposta_segundos, deteccao_ativa) VALUES
 -- 16 tipos restantes: copie nome, categoria, severidade_padrao, cor, descricao e tempo_resposta_segundos
 -- de frontend/src/mockData/mockEvents.ts (eventTypesCatalog). icone = o próprio codigo. deteccao_ativa = 0.
 ...;
-- e UPDATE de tempo_resposta_segundos dos 4 existentes com os valores do mesmo catálogo.
```
Os 16 códigos: `panic_button`, `geofence_exit`, `geofence_entry`, `tamper_detected`, `theft_suspected`, `collision_detected`, `towing_detected`, `unusual_hours`, `fatigue_suspected`, `distracted_driving`, `aggressive_driving`, `excessive_idle`, `route_deviation`, `low_battery`, `fuel_waste_detected`, `maintenance_due`. Referência de categoria e severidade: `aitrackdatadrivr/MONITORAMENTO_EVENTOS.md` (tabelas nas linhas ~155, ~238, ~341).

**Atenção:** `save_event_to_db` (T0.7) só persiste tipos que existem em `tipo_evento`. Inserir os 16 **não** muda nada até a Fase 4 gerar esses eventos.

**Backend:** `/api/events/catalog` retorna todos os campos, incluindo `tempo_resposta_segundos` e `deteccao_ativa` (bool).
**Frontend** `EventsCatalog.tsx`:
- catálogo por `eventService.getCatalog()` e estatísticas por `eventService.getStats()` (formato de T0.8);
- badge "Detecção ativa" ou "Planejado" conforme `deteccao_ativa`;
- ícones por `eventIcons.ts`.

### T3.6 — Remover mocks e código morto

- Apagar `src/mockData/` e `src/components/VehicleList.tsx` (não usado).
- `grep -rn "mockData\|mockAlerts\|mockEvents\|mockMonitors" src` deve retornar vazio.
- Adicionar no topo de `aitrackdatadrivr/MANUAL_MOCK.md`: `> OBSOLETO desde a Fase 3 do HANDOFF_MONITORES_IA.md — o App 2 não usa mais dados mock.`

### T3.7 — Validação visual e de regressão

1. Criar `aitrackdatadrivr/tests/app2_screenshots.py` (Playwright, Chromium headless, viewport 1600×950):
   - abre `http://localhost:3003`, clica nas 6 abas, espera 6 s em cada (a página faz polling; **não** use `wait_until="networkidle"`, que nunca conclui) e salva PNGs em `aitrackdatadrivr/tests/reports/screenshots/`, pasta que deve ir para o `.gitignore`;
   - na aba Monitores AI, seleciona o monitor #4 e captura também o detalhe;
   - falha se o texto "Mock" ou "Carregando" permanecer visível após a espera.
2. **Critério de aceite da Fase 3:**
   - `npx tsc --noEmit` e `npm run build` sem erro.
   - Nenhuma referência a mock (T3.6).
   - Aba Alertas lista os alertas do banco (mesma contagem de `GET /api/alerts`). Reconhecer, Resolver e Descartar alteram `status` no banco, conferido por SQL.
   - Aba Monitores mostra análises reais com badge IA. "Analisar agora" cria uma análise nova.
   - Detalhe do monitor mostra eventos do banco dos veículos daquele monitor.
   - Catálogo lista 20 tipos, 4 com "Detecção ativa".
   - **App 1** (3001): lista 20 veículos, mapa centraliza ao selecionar `SIM-1000` e `SIM-D1`. Rode também o `playwright`/capture equivalente ou verifique manualmente com screenshots.

---

## 8. FASE 4 — Cobertura de eventos e motoristas do app

### T4.1 — Dados de ignição e bateria até o motor

`db_handler.save_location` hoje repassa ao motor só `lat`, `lon`, `speed`, `heading` e `timestamp`. Acrescentar `ignition` (bool | None), `battery_voltage` (float | None) e `altitude`. Os parsers já extraem esses campos (ver `protocol_parsers.py`; confirme para cada protocolo). Maxtrack não tem `device_id`: usa `FK-<VEICOD>`.

### T4.2 — Detectores novos

Organização: criar `server/detectores/` com um módulo por grupo (`seguranca.py`, `operacao.py`, `composicao.py`). Cada detector é uma **função pura**: recebe o histórico recente do veículo, a posição atual e o estado do detector; devolve eventos. `behavioral_engine.add_position` chama um **registro** de detectores ativos. Estado por veículo e por detector fica em memória, sob o lock.

Implemente **somente os tipos do Grupo A**. Todos os limites vão para constantes lidas do env. Ao ativar um tipo, faça `UPDATE tracker.tipo_evento SET deteccao_ativa=1 WHERE codigo=...` numa migration `011_...` e seguintes.

**Grupo A: implementar**

| Código | Regra (defaults) | Severidade | Antirrepetição |
|---|---|---|---|
| `excessive_idle` | `ignition=True` e `speed < 3` contínuos por ≥ **5 min** | medium; high se ≥ 20 min | 1 por episódio (termina com speed ≥ 3 ou ignition=False) |
| `low_battery` | `battery_voltage < 11.8` V | medium; high se < 11.0 | no máx. 1 a cada 30 min |
| `tamper_detected` | `battery_voltage < 3.0` V com leitura anterior ≥ 11.0 V (corte de alimentação) | critical | 1 por episódio |
| `unusual_hours` | `speed > 5` com `ignition=True` entre **23:00 e 05:00** (hora local; env `HORARIO_INCOMUM_INICIO/FIM`) | critical (catálogo) | 1 por noite por veículo |
| `towing_detected` | `ignition=False` e `speed > 10` em **2 amostras consecutivas** | high | 1 por episódio |
| `collision_detected` | desaceleração ≥ **25 km/h/s** (T0.5) seguida de `speed < 5` em até 2 amostras | critical | 1 a cada 10 min |
| `aggressive_driving` | ≥ **4** eventos `harsh_accel`/`harsh_brake`/`sharp_turn` do veículo em **10 min** | high | no máx. 1 a cada 30 min |
| `fatigue_suspected` | condução contínua ≥ **4 h**, sem parada (speed < 5) de ≥ 15 min | high | 1 por episódio |
| `theft_suspected` | `unusual_hours` **e** (`towing_detected` **ou** `geofence_exit`) do mesmo veículo em 30 min | critical | 1 a cada 2 h |
| `geofence_exit` / `geofence_entry` | ver T4.3 | critical | 1 por transição |
| `route_deviation` | ver T4.4 | medium | 1 por episódio |
| `maintenance_due` | ver T4.5 | medium | 1 por dia por veículo |
| `fuel_waste_detected` | por dia: minutos ociosos (idle) ≥ 60 **ou** ≥ 20 `harsh_accel` no dia | low | 1 por dia por veículo |

Pesos no score (T0.6): acrescentar `aggressive_driving: 4.0` e `fatigue_suspected: 3.0`. Os demais tipos **não** afetam o score comportamental.

**Grupo B: não implementar sem documentação do protocolo**

- `panic_button`: exige mensagens de alarme do protocolo (ex.: SOS do Queclink/Suntech). Os parsers atuais tratam só relatório de posição. **Implemente somente com a documentação oficial do protocolo em mãos; não invente formato.** Sem documentação, mantenha `deteccao_ativa=0` e registre na seção 10.
- `distracted_driving`: exige câmera ou sensor de celular, que não existem. Manter `deteccao_ativa=0`, com `descricao` indicando o motivo.

### T4.3 — Geocercas

- A tabela `tracker.geocercas` existe (0 linhas). Migration: `ADD COLUMN IF NOT EXISTS GCER_TIPO ENUM('permitida','proibida') NOT NULL DEFAULT 'permitida'`.
- Associação: geocercas com `FK_USUCOD` valem para veículos com o mesmo `veiculos.FK_USUCOD`; geocercas com `FK_USUCOD` NULL valem para todos.
- Carregar polígonos com `ST_AsText(GCER_AREA)`, cache de 60 s. Ponto-em-polígono em Python (ray casting), **sem nova dependência**.
- `geofence_exit`: estava dentro de uma `permitida` e saiu. `geofence_entry`: entrou numa `proibida`. Estado dentro/fora por veículo × geocerca.
- CRUD mínimo na API: `GET/POST/DELETE /api/geofences`, com polígono em GeoJSON na API, convertido para WKT no banco. Tela no App 2 é opcional nesta fase.
- Teste: geocerca de teste cobrindo parte de uma rota do simulador.

### T4.4 — Desvio de rota

- Migration: `tracker.rota_veiculo (id PK, veicod INT NOT NULL, nome VARCHAR(100), pontos LONGTEXT NOT NULL /* JSON [[lat,lon],...] */, tolerancia_m INT NOT NULL DEFAULT 300, ativa TINYINT(1) DEFAULT 1)`.
- Só avalia veículos com rota ativa. Distância ponto → polilinha (haversine sobre projeção no segmento) > tolerância em **2 amostras consecutivas** → `route_deviation`. Termina ao voltar para dentro.
- Para testes, cadastrar como rota de `SIM-1000` a rota que o simulador usa (`config/routes.json`).

### T4.5 — Manutenção

- Migration: `tracker.manutencao_veiculo (veicod INT PK, data_ultima DATE NOT NULL, km_ultima DOUBLE NOT NULL DEFAULT 0, intervalo_km INT NOT NULL DEFAULT 10000, intervalo_dias INT NOT NULL DEFAULT 180)`.
- Uma vez por dia, na thread do motor: para veículos cadastrados, somar a distância percorrida desde `data_ultima` (haversine entre posições consecutivas de `tracker.localizacao` por `FK_VEICOD`, em lotes por dia).
  - Antes, verifique os índices de `localizacao` (`SHOW INDEX`). Se não houver índice em `(FK_VEICOD, DATAHORA)`, crie-o numa migration, avisando que a tabela é grande.
- Devida se `km ≥ intervalo_km` ou `dias ≥ intervalo_dias`.

### T4.6 — Motoristas do app Dirijabem nos monitores

**Contexto:**
- `dirijabem.viagem(CODVIA, CODUSU, PLACA, DATAHORINI, DATAHORFIN, SCORE, ...)`;
- `dirijabem.localizacaodados(LOCDADCOD, CODVIA, DATAHORA, VELATU, ACELLINATU, ACELGPSATU, VARDIRATU, coords)`, ~60 mi linhas, índices só em `LOCDADCOD` e `CODVIA`;
- o código que já lê `coords` corretamente está em `server/dirijabem_api.py` (`get_user_route`, ~l.185): reutilize a conversão;
- `tracker.eventos.veicod` é **NOT NULL** com FK para `veiculos`, e motoristas do app não têm `VEICOD`.

**O que fazer:**
1. **Migration** (tabela grande; `MODIFY` recria a tabela e pode levar minutos):
   ```sql
   ALTER TABLE tracker.eventos
     MODIFY veicod INT NULL,
     ADD COLUMN IF NOT EXISTS codusu INT NULL;
   CREATE INDEX IF NOT EXISTS idx_eventos_codusu_ts ON tracker.eventos (codusu, `timestamp`);
   CREATE TABLE IF NOT EXISTS tracker.ingest_watermark (
     fonte VARCHAR(50) PRIMARY KEY, ultimo_id BIGINT NOT NULL DEFAULT 0, atualizado_em DATETIME NULL);
   ```
2. **Convenção de `device_id`** para motoristas do app: `APP-<CODUSU>`. **Não** altere `tracker.veiculo_unificado`, que é usada pelo App 1.
3. **`server/dirijabem_ingest.py`**, thread iniciada no `run.py` com env `DIRIJABEM_INGEST_HABILITADO=1`; roda a cada 10 s:
   - CODUSUs alvo = `SELECT DISTINCT codusu_dirijabem FROM tracker.veiculomonitor WHERE tipo_veiculo='dirijabem' AND ativo=1`. Se vazio, não faz nada.
   - Viagens recentes: `SELECT CODVIA, CODUSU FROM dirijabem.viagem WHERE CODUSU IN (...) AND DATAHORINI >= NOW() - INTERVAL 1 DAY`.
   - Pontos novos: `SELECT LOCDADCOD, CODVIA, DATAHORA, VELATU, ACELLINATU, VARDIRATU, coords FROM dirijabem.localizacaodados WHERE CODVIA IN (...) AND LOCDADCOD > %s ORDER BY LOCDADCOD LIMIT 5000`, com watermark `fonte='dirijabem_localizacaodados'`.
   - Para cada ponto: `behavioral_engine.add_position("APP-<codusu>", {lat, lon, speed=VELATU, heading=?, timestamp=DATAHORA, codusu=...})`.
   - **Unidades desconhecidas:** antes de usar `ACELLINATU` e `VARDIRATU`, inspecione a distribuição (`MIN/MAX/AVG` numa amostra de 10 mil linhas por `CODVIA`) e o código que os gera (`dirijabem_simulator.py` e `dirijabem_continuous_simulator.py`, procure `ACELLINATU`). Se a unidade não ficar clara, **não use** esses campos: calcule por Δv/Δt e rumo entre coordenadas. Registre a conclusão na seção 10.
   - Atualiza o watermark após processar o lote.
4. Persistência (T0.7): eventos com `codusu` e sem `veicod` passam a ser gravados (`veicod` NULL, `codusu` preenchido).
5. Motor de monitores: `get_monitor_vehicles` já traz `tipo_veiculo` e `codusu_dirijabem`. Para `dirijabem`, `device_id = APP-<codusu>`. Contexto do LLM: `veiculo.tipo = "app"` e, se existir, `score_app` = `SCORE` da viagem mais recente de `dirijabem.viagem`.
6. API: `POST /api/monitors/<id>/vehicles` aceita `{tipo_veiculo: "dirijabem", codusu}`, com `device_id` gerado. Frontend (T3.3 item 6) passa a permitir adicionar veículos `app_only` pelo `codusu` de `/api/vehicles/unified`.

**Critério de aceite de T4.6:**
- Com o simulador Dirijabem rodando e o `codusu` 1 adicionado ao monitor #4, em 15 min surgem eventos com `device_id='APP-1'` em `tracker.eventos` e análises desse veículo em `monitor_analises`.
- App 1 continua ok.

### T4.7 — Simulador com cenários e testes

- `aitrackdatadrivr/simulator.py --cenario <nome>` com um veículo extra (`SIM-9000`) que reproduz cada situação do Grupo A: `idle`, `bateria_baixa`, `corte_energia`, `madrugada`, `reboque`, `colisao`, `agressivo`, `fadiga` (aceleração de tempo permitida), `geocerca`, `desvio_rota`.
- Testes unitários por detector em `aitrackdatadrivr/tests/test_detectores.py`, com sequências sintéticas, sem banco.
- **Critério de aceite da Fase 4:**
  - cada tipo do Grupo A tem teste unitário passando;
  - cada tipo gera ≥ 1 evento real em `tracker.eventos` rodando o cenário correspondente;
  - tipos implementados com `deteccao_ativa=1`;
  - Grupo B documentado.

---

## 9. Definição de pronto global

- [ ] Fases 0–4 com todos os critérios de aceite atendidos e registrados na seção 10.
- [ ] `cd aitrackdatadrivr && .venv/bin/python -m pytest -q tests` passando.
- [ ] `cd aitrackdatadrivr/frontend && npx tsc --noEmit && npm run build` sem erros.
- [ ] Backend estável por **2 h** com os dois simuladores: RSS < 400 MB, `eventos_descartados` = 0, motor sem exceções não tratadas no log.
- [ ] App 1 sem regressão (lista, mapa, `SIM-D1`).
- [ ] Nenhuma credencial no código ou no git (`git log -p | grep -i password` sem senhas reais).
- [ ] Documentação atualizada:
  - `AGENTS.md`, `CLAUDE.md`, `comorodartudo.md` e `aitrackdatadrivr/COMO_RODAR.md` refletem o sistema final (venv, portas, novos envs e threads);
  - Apêndice A deste documento atualizado com os endpoints finais.
- [ ] `AUDITORIA_APP2_DATADRIVR.md`: acrescentar no topo `> Situação posterior: ver HANDOFF_MONITORES_IA.md, seção 10.`

---

## 10. Registro de progresso

> Uma linha por tarefa concluída ou interrompida. Inclua valores medidos quando o critério pedir.

| Data | Tarefa | Commit | Resultado / medições / desvios |
|---|---|---|---|
| 2026-09-16 | Handoff | — | Documento criado. Estado inicial: ver `AUDITORIA_APP2_DATADRIVR.md`. Nenhuma tarefa iniciada. |

---

## Apêndice A — Endpoints

### A.1 Existentes (commit `186050a`)

| Método | Rota | Arquivo | Usado por |
|---|---|---|---|
| GET | `/api/posicoes` | api.py | App 1, App 2 |
| GET | `/api/positions/history/<veicod>`, `/latest/<veicod>`, `/updates/<veicod>` | api.py | App 1, App 2 (`latest`) |
| GET | `/api/fleet/scores`, `/api/fleet/events`, `/api/fleet/stats` | api.py | App 2 |
| GET | `/api/vehicles/<device_id>/score` | api.py | — |
| GET/POST | `/api/monitors` | monitor_api.py | App 2 (GET) |
| GET/PUT | `/api/monitors/<id>` | monitor_api.py | App 2 (GET) |
| POST | `/api/monitors/<id>/toggle` | monitor_api.py | — |
| GET/POST | `/api/monitors/<id>/vehicles` | monitor_api.py | App 2 (GET) |
| DELETE | `/api/monitors/vehicles/<veiculomonitor_id>` | monitor_api.py | — |
| GET | `/api/monitors/<id>/analyses` | monitor_api.py | — |
| GET | `/api/monitors/stats` | monitor_api.py | — |
| GET | `/api/alerts`, `/api/alerts/<id>`, `/api/alerts/stats` | monitor_api.py | — |
| PUT | `/api/alerts/<id>/acknowledge` (body `{reconhecido_por}`), `/resolve`, `/dismiss` | monitor_api.py | — |
| GET | `/api/events`, `/api/events/catalog`, `/api/events/stats` | monitor_api.py | — |
| GET | `/api/vehicles/unified`, `/api/monitors/<id>/vehicles/unified` | monitor_api.py | — |
| GET | `/api/unified/vehicles`, `/vehicle/<placa>`, `/position/<placa>`, `/stats` | unified_api.py | App 1 |
| GET/POST | `/api/dirijabem/users`, `/user/<codusu>/start`, `/start-synthetic`, `/stop`, `/position`, `/last-point`, `/route`, `/status` | dirijabem_api.py | App 2 |

### A.2 Novos ou alterados por este handoff

| Método | Rota | Tarefa |
|---|---|---|
| GET | `/api/fleet/health` | T0.7 |
| GET | `/api/events` (+ `desde`, `ate`, `monitor_id`, limite máx. 500) | T0.8 |
| GET | `/api/events/stats` (novo formato) | T0.8 |
| POST | `/api/monitors/<id>/analyze` | T1.5 |
| GET | `/api/monitors/engine/status` | T1.5, T2.5 |
| GET | `/api/monitors/<id>/analyses` (+ campos LLM, `limit`) | T1.5, T2.5 |
| GET | `/api/alerts` (+ `monitor_nome`, dados da análise, `device_id`, `limit`) | T2.5 |
| GET | `/api/alerts/stats` (inteiros + novos campos) | T3.2 |
| POST | `/api/monitors/<id>/vehicles` (aceita `{device_id}` ou `{tipo_veiculo:"dirijabem", codusu}`) | T3.3, T4.6 |
| GET | `/api/events/catalog` (+ `tempo_resposta_segundos`, `deteccao_ativa`) | T3.5 |
| GET/POST/DELETE | `/api/geofences` | T4.3 |

---

## Apêndice B — Comandos úteis de diagnóstico

```bash
# Processos e portas deste projeto
ss -ltnp | grep -E ':(5009|9000|3001|3003)\b'
ps -o pid,rss,etime,cmd -p <PID>

# Tempo de endpoint (mediana manual de 3 execuções)
for i in 1 2 3; do curl -s -o /dev/null -w '%{time_total}\n' 'localhost:5009/api/events/stats'; done

# Contagens principais (via cliente mysql; a senha será pedida)
mysql -h camerascasas.no-ip.info -P 3307 -u scadabr -p -e "
  SELECT (SELECT COUNT(*) FROM tracker.monitor_analises) analises,
         (SELECT COUNT(*) FROM tracker.monitor_alertas) alertas,
         (SELECT COUNT(*) FROM tracker.eventos WHERE timestamp >= CURDATE()) eventos_hoje;"

# Alertas duplicados (deve voltar vazio)
mysql ... -e "SELECT monitor_id, veiculomonitor_id, severidade, COUNT(*) FROM tracker.monitor_alertas
              WHERE status='pending' AND criado_em >= NOW() - INTERVAL 60 MINUTE GROUP BY 1,2,3 HAVING COUNT(*)>1;"

# Scores por perfil do simulador
curl -s localhost:5009/api/fleet/scores | python3 -c "
import sys,json; s=json.load(sys.stdin)
g=[s.get(f'SIM-{i}') for i in range(1000,1005)]; m=[s.get(f'SIM-{i}') for i in range(1005,1008)]; p=[s.get(f'SIM-{i}') for i in (1008,1009)]
avg=lambda l:[x for x in l if x is not None] and sum(x for x in l if x is not None)/len([x for x in l if x is not None])
print('good',avg(g),'moderate',avg(m),'poor',avg(p))"
```
