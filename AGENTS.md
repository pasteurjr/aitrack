# AGENTS.md — Instruções para agentes de código (Codex e outros)

> Leia este arquivo **inteiro** antes de mexer em qualquer coisa. Depois leia, nesta ordem:
> 1. `AUDITORIA_APP2_DATADRIVR.md`: diagnóstico do estado atual (o que funciona, o que é mock, o que está quebrado).
> 2. `HANDOFF_MONITORES_IA.md`: **especificação de execução**. É a fonte de verdade do que fazer, em que ordem e como provar que está pronto.
>
> Se algum outro documento do repositório contradisser estes três, **estes três valem**. Os `PLAN_*.md`, `PLANO_V2.md` e `MANUAL_MOCK.md` são históricos.

---

## 1. O que é este repositório

Sistema de rastreamento veicular com análise comportamental de motoristas. Tem **duas aplicações web** que compartilham **um único backend**:

| App | Pasta do frontend | Porta | Função |
|---|---|---|---|
| App 1 — AITrack | `frontend/` | 3001 | Mapa com posições ao vivo e lista unificada de veículos |
| App 2 — AITrack + DataDrivr | `aitrackdatadrivr/frontend/` | 3003 | Dashboard comportamental, monitores de IA, alertas, eventos |
| Backend (ambos) | `aitrackdatadrivr/` | API **5009**, socket TCP **9000** | Recebe GPS, detecta eventos, serve a API |

Stack: Python 3.13 (Flask, mysql-connector) · React 19 + TypeScript 4.9 (create-react-app) + Leaflet · MySQL/MariaDB remoto.

---

## 2. Mapa do repositório: o que é ativo e o que não mexer

| Caminho | Situação | Regra |
|---|---|---|
| `aitrackdatadrivr/run.py` | ✅ **ATIVO**: backend que roda de verdade | Ponto de entrada do backend |
| `aitrackdatadrivr/server/` | ✅ **ATIVO**: todo o código do backend | Trabalhe aqui |
| `aitrackdatadrivr/simulator.py` | ✅ **ATIVO**: simulador de rastreadores com perfis de motorista | Use este |
| `aitrackdatadrivr/dirijabem_*.py` | ✅ ativo: simuladores e replay do app Dirijabem | — |
| `aitrackdatadrivr/migrations/` | ✅ ativo: SQL do schema | Novas migrations a partir de `005_` |
| `aitrackdatadrivr/frontend/` | ✅ **ATIVO**: App 2 | Trabalhe aqui |
| `frontend/` (raiz) | ✅ ativo: App 1 | **Não quebre.** Usa `/api/unified/*`, `/api/positions/latest/*`, `/api/posicoes` |
| `run.py` (raiz) | ❌ **LEGADO E QUEBRADO**: importa `server.monitor_engine`, que não existe em `server/` da raiz | **Não use, não conserte** |
| `server/` (raiz) | ❌ **LEGADO**: backend antigo do App 1 | **Não use** |
| `simulator.py` (raiz) | ⚠️ legado: sorteia velocidade e rumo a cada pacote e gera eventos falsos | Não use para testar comportamento |
| `tests/` (raiz) | ✅ testes pytest de parsers + validadores de API/Playwright | Pode ampliar |
| `CLAUDE.md` | instruções do Claude Code | Mantenha coerente com este arquivo |
| `../aitrackdatadrivr`, `../datadrivr` (pastas **irmãs**, fora do repo) | ❌ outros projetos | **Nunca edite** |
| `*.sql` grandes na raiz, `TUDO.MD`, `VERGONHA.md`, `sessao*.txt` | arquivos históricos | Ignore |

---

## 3. Ambiente e comandos

### 3.1 Pré-requisitos
- Python 3.13 (hoje é o do miniconda: `/home/pasteurjr/miniconda3/bin/python3`)
- Node v22 via nvm, npm 10
- Clientes `mysql` e `mysqldump` instalados em `/usr/bin`

### 3.2 Ambiente Python do backend
O backend **roda com o Python global do miniconda**, compartilhado com outros projetos do usuário. A Fase 0 (tarefa T0.1 do handoff) cria um venv próprio em `aitrackdatadrivr/.venv`. Depois dela, use sempre:
```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
source .venv/bin/activate
```
**Nunca** rode `pip install` ou atualize pacotes no Python global. Isso quebra outros projetos da máquina.

### 3.3 Subir o sistema (sempre a partir de `aitrackdatadrivr/`)
Até a tarefa T0.2 do handoff, o diretório de trabalho importa: `env_loader` lê `config/.env` e `routes_loader` lê `config/routes.json` **relativos ao diretório atual**. Depois de T0.2 isso deixa de ser necessário, mas continue iniciando a partir de `aitrackdatadrivr/`.

```bash
# Terminal 1 — backend (API 5009 + socket 9000 + replay Dirijabem)
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr && python3 run.py

# Terminal 2 — simulador de rastreadores (10 veículos SIM-1000..SIM-1009)
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr && python3 simulator.py

# Terminal 3 — simulador Dirijabem (opcional)
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr && python3 dirijabem_continuous_simulator.py --drivers 5 --speed 10

# Terminal 4 — App 2
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr/frontend && PORT=3003 BROWSER=none npm start

# Terminal 5 — App 1
cd /home/pasteurjr/progreact/aitrack/frontend && PORT=3001 BROWSER=none npm start
```

**Portas 3000 e 3002 pertencem a OUTROS projetos do usuário.** Nunca mate processos nessas portas.

### 3.4 Parar o sistema
Mate **somente pelo PID** que você iniciou, ou pelas portas deste projeto:
```bash
ss -ltnp | grep -E ':(5009|9000|3001|3003)\b'   # descobrir PIDs
kill <PID>
```
**Proibido:** `pkill node`, `pkill python`, `killall`. Há outros projetos e outras sessões de agentes rodando na máquina.

### 3.5 Verificações rápidas
```bash
curl -s localhost:5009/api/monitors/stats
curl -s localhost:5009/api/fleet/scores
curl -s localhost:5009/api/unified/vehicles | head -c 300   # App 1 continua ok?
```

### 3.6 Testes
```bash
# Testes do backend ativo (criados em T0.10), sempre com o venv
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr && .venv/bin/python -m pytest -q tests

# Testes antigos da raiz (parsers do backend LEGADO): não são referência para o backend ativo
cd /home/pasteurjr/progreact/aitrack && python3 -m pytest -q tests/test_protocol_parsers.py

# Frontend App 2: checagem de tipos e build
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr/frontend && npx tsc --noEmit && npm run build
```

---

## 4. Banco de dados: REGRAS DE SEGURANÇA (obrigatório)

O banco é **remoto, compartilhado e com dados reais**: `camerascasas.no-ip.info:3307`.

1. **O servidor hospeda 35+ bancos de outros sistemas** (ERP, produção etc.). O usuário `scadabr` tem `ALL PRIVILEGES ON *.*`. Um erro pode destruir outro sistema.
   - Você **só pode escrever** no banco **`tracker`**.
   - O banco **`dirijabem`** é **somente leitura** para você. Exceção: os simuladores Dirijabem, que já escrevem lá.
   - **Nunca** rode SQL sem o nome do banco explícito ou fora de `tracker`/`dirijabem`.
2. **Tabelas grandes:** `tracker.localizacao` (~4,3 mi), `tracker.eventos` (~2,6 mi, cresce ~100 mil/dia), `dirijabem.localizacaodados` (~60 mi).
   - Nunca rode `SELECT` sem `WHERE` indexado ou sem `LIMIT` nelas.
   - Nunca use `DATE(coluna) = ...`. Use intervalo: `coluna >= X AND coluna < Y`.
   - `ALTER TABLE`/`CREATE INDEX` nelas pode demorar minutos. Avise no log do commit.
3. **Nunca** `DROP TABLE`, `TRUNCATE` ou `DELETE` sem `WHERE` em qualquer tabela.
   - Exclusões permitidas estão listadas explicitamente no handoff. Exemplo: apagar os 4 alertas mock.
4. **Backup antes de migration que altera ou remove dados:**
   ```bash
   mysqldump -h camerascasas.no-ip.info -P 3307 -u scadabr -p tracker <tabela> > aitrackdatadrivr/migrations/backup/<data>_<tabela>.sql
   ```
   A pasta `migrations/backup/` deve ficar no `.gitignore`.
5. **Migrations:**
   - Novos arquivos `aitrackdatadrivr/migrations/NNN_descricao.sql`, a partir de `005`.
   - Devem ser **idempotentes** quando possível (`IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`; o servidor é MariaDB e aceita).
   - Aplique com o runner criado em T0.1 (`python migrations/apply.py`), que registra em `tracker.schema_migrations`.
   - As migrations `001`–`004` **já estão aplicadas**. Não reaplique.
6. **Credenciais:**
   - Ficam em `aitrackdatadrivr/config/.env` (ignorado pelo git).
   - Hoje há credenciais **escritas no código** em vários arquivos, com dois usuários: `scadabr` para `tracker` e `producao` para `dirijabem`/unificado. A tarefa T0.2 centraliza isso.
   - **Nunca** copie senhas para documentos, commits, logs ou mensagens.
   - A chave da Anthropic vai em `ANTHROPIC_API_KEY` no mesmo `.env`.

---

## 5. Git

- Branch: **`main`**, com commit e **push direto** (`git push origin main`). Autorizado pelo dono do projeto.
- **Um commit por tarefa** do handoff (ex.: `T0.3`). Mensagem no formato:
  ```
  <tipo>(<escopo>): <resumo>  [T0.3]

  <o que mudou e por quê, 2–5 linhas>
  <como foi verificado>
  ```
  `tipo` ∈ `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`.
- Antes de cada commit: testes da fase passando, `git status` sem arquivos acidentais. Nada de `.env`, `node_modules`, `build/`, `__pycache__`, logs ou backups.
- Antes do push: `git pull --rebase origin main`. Outra instância (Claude Code) pode trabalhar no mesmo repositório.
- **Ao terminar cada tarefa**, atualize a seção "Registro de progresso" no fim de `HANDOFF_MONITORES_IA.md` com data, tarefa, commit e observações. É assim que o próximo agente sabe onde você parou.

---

## 6. Convenções de código

- **Backend:**
  - Imports **relativos** dentro de `server/` (`from .behavioral_engine import ...`). O import absoluto `from behavioral_engine import ...` **falha** e já causou bug.
  - Use `logging` em vez de `print` no código novo.
  - Constantes configuráveis ficam no topo do módulo, lidas do `.env` com default.
  - SQL sempre parametrizado (`%s`).
- **Contratos de API:** não mude o formato das respostas existentes usadas pelo App 1 ou pelo App 2 sem ajustar o frontend no **mesmo commit**. Campos novos podem ser adicionados.
- **Frontend:**
  - Tipos em `src/types/`.
  - Chamadas HTTP pelo `src/services/apiService.ts`. Não espalhe `axios.get('http://localhost:5009...')` em componentes novos.
  - Textos da interface em **português**.
- **Idioma:** comentários e documentação em português. Nomes de código seguem o padrão existente, que mistura português e inglês. Não renomeie o que já existe.

---

## 7. Armadilhas conhecidas (leia antes de depurar)

1. **Estado em memória:** `server/behavioral_engine.py` guarda scores e eventos em memória do processo. Tudo que lê esse estado precisa rodar **no mesmo processo** do `run.py`. Reiniciar o backend zera scores e a lista de eventos. O banco não é afetado.
2. **Testes que chamam `add_position`** gravam em `tracker.eventos`. Em testes, faça monkeypatch da persistência.
3. **Timestamps:** o `db_handler` passa `datetime.now()` (hora local de recebimento) ao motor, não a hora do pacote (UTC). Não misture as duas.
4. **Maxtrack não envia device_id:** o veículo vira `FK-<VEICOD>` no motor.
5. **`eventos.veicod` é `NOT NULL` com FK para `veiculos`:** motoristas só do app Dirijabem não têm `VEICOD`. Ver T4.2.
6. **CRA e `CI=true`:** `npm run build` com `CI=true` trata warnings como erro.
7. **Existe build antigo** em `aitrackdatadrivr/frontend/build/`. Não o use para validar.
