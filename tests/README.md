# 🧪 Sistema de Validação Automática - AITrack Monitor System

Este diretório contém scripts de validação automática que testam todos os endpoints da API e geram relatórios detalhados com capturas de tela.

## 📁 Estrutura

```
tests/
├── README.md                    # Este arquivo
├── api_validator.py             # Validador de API (testa endpoints)
├── playwright_validator.py      # Capturador de screenshots
├── run_validation.py            # Script principal (executa tudo)
└── reports/                     # Relatórios gerados
    ├── DEMO_VALIDATION_REPORT.md    # Exemplo de resultado
    ├── validation_report_*.md       # Relatórios de testes
    ├── visual_report_*.md           # Relatórios visuais
    ├── CONSOLIDATED_REPORT.md       # Relatório consolidado
    └── screenshots/                 # Capturas de tela
```

## 🚀 Como Usar

### Pré-requisitos

```bash
# Instalar dependências de teste
pip install -r requirements-tests.txt

# Para screenshots (opcional)
playwright install chromium
```

### Opção 1: Validação Completa (Recomendado)

```bash
# 1. Iniciar o servidor em um terminal
python run.py

# 2. Em outro terminal, executar validação
python tests/run_validation.py
```

Isso irá:
- ✅ Testar todos os 21 endpoints da API
- ✅ Capturar 8+ screenshots das respostas
- ✅ Gerar 3 relatórios em Markdown
- ✅ Salvar tudo em `tests/reports/`

### Opção 2: Apenas Testes de API (Rápido)

```bash
# Servidor deve estar rodando
python tests/api_validator.py
```

Gera apenas o relatório de testes sem screenshots.

### Opção 3: Apenas Screenshots (Visual)

```bash
# Requer Playwright instalado
python tests/playwright_validator.py
```

Captura screenshots de todos os endpoints.

## 📊 Relatórios Gerados

### 1. Validation Report (API Tests)

**Arquivo:** `validation_report_TIMESTAMP.md`

Contém:
- ✅ Resumo executivo (total, sucessos, falhas)
- 📊 Estatísticas por categoria (Monitors, Alerts, Events, etc.)
- 📋 Detalhes de cada teste com requisições e respostas
- 🎯 Taxa de sucesso geral

### 2. Visual Report (Screenshots)

**Arquivo:** `visual_report_TIMESTAMP.md`

Contém:
- 📸 Screenshots de cada endpoint
- 🖼️ Visualização formatada das respostas JSON
- 📊 Estatísticas visuais

### 3. Consolidated Report

**Arquivo:** `CONSOLIDATED_REPORT.md`

Contém:
- 📈 Resumo executivo completo
- 🔗 Links para relatórios detalhados
- 📋 Instruções de uso
- 🎯 Próximos passos

## 🧪 Endpoints Testados

### Monitors (4 testes)
- `GET /api/monitors` - Lista todos
- `GET /api/monitors/1` - Busca por ID
- `GET /api/monitors/999` - Teste 404
- `GET /api/monitors/stats` - Estatísticas

### Vehicles (3 testes)
- `GET /api/monitors/1/vehicles` - Veículos do monitor
- `GET /api/monitors/2/vehicles` - Outro monitor
- `GET /api/vehicles/SIM-1000/score` - Score específico

### Analyses (2 testes)
- `GET /api/monitors/1/analyses` - Análises
- `GET /api/monitors/1/analyses?limit=10` - Com limite

### Alerts (5 testes)
- `GET /api/alerts` - Todos os alertas
- `GET /api/alerts?status=pending` - Filtro por status
- `GET /api/alerts?severidade=critical` - Filtro por severidade
- `GET /api/alerts/stats` - Estatísticas
- `GET /api/alerts/1` - Alerta específico

### Events (5 testes)
- `GET /api/events/catalog` - Catálogo de tipos
- `GET /api/events?limit=10` - Histórico
- `GET /api/events?device_id=SIM-1000` - Por veículo
- `GET /api/events/stats` - Estatísticas
- `GET /api/fleet/events?limit=20` - Eventos comportamentais

### Fleet (2 testes)
- `GET /api/fleet/scores` - Scores de todos os veículos
- `GET /api/fleet/stats` - Estatísticas da frota

**Total: 21 endpoints testados**

## 📸 Exemplos de Screenshots

Quando Playwright está instalado, você verá screenshots como:

### Lista de Monitores
![Monitors](screenshots/_monitors.png)

### Alertas Pendentes
![Alerts](screenshots/_alerts.png)

### Catálogo de Eventos
![Events Catalog](screenshots/_events_catalog.png)

## ❌ Troubleshooting

### Erro: "Connection refused"

**Causa:** Servidor não está rodando

**Solução:**
```bash
python run.py
```

### Erro: "No module named 'playwright'"

**Causa:** Playwright não instalado

**Solução:**
```bash
pip install playwright
playwright install chromium
```

### Todos os testes falharam

**Verificar:**
1. Servidor está rodando? `python run.py`
2. Porta 5009 está livre? `netstat -an | grep 5009`
3. Banco de dados está acessível?

## 🎯 Resultado Esperado

### ✅ Se tudo estiver OK:

```
🧪 Iniciando validação da API...
================================================================================

📊 Testando endpoints de MONITORS...
✅ GET /monitors - 200 OK
✅ GET /monitors/1 - 200 OK
✅ GET /monitors/999 - 404 Not Found
✅ GET /monitors/stats - 200 OK

[...]

================================================================================
✅ Testes concluídos: 21/21 passaram
❌ Falhas: 0
================================================================================

📄 Relatório salvo em: tests/reports/validation_report_20260302_171500.md
```

### ❌ Se houver problemas:

```
❌ Testes concluídos: 0/21 passaram
❌ Falhas: 21
```

Verifique os logs no relatório gerado.

## 📝 Adicionando Novos Testes

Para adicionar um novo teste, edite `api_validator.py`:

```python
self.test_endpoint(
    "GET",                          # Método HTTP
    "/novo/endpoint",               # Endpoint
    "Descrição do teste",           # Nome
    expected_status=200,            # Status esperado
    data=None                       # Dados (para POST/PUT)
)
```

## 🔄 Automação

Você pode integrar estes testes em CI/CD:

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements-tests.txt
      - name: Start server
        run: python run.py &
      - name: Run tests
        run: python tests/api_validator.py
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: tests/reports/
```

## 📚 Mais Informações

- Ver relatório de demonstração: [DEMO_VALIDATION_REPORT.md](reports/DEMO_VALIDATION_REPORT.md)
- Documentação da API: Ver Swagger/OpenAPI (futuro)
- Issues/Bugs: Reportar no GitHub

---

*Sistema de validação automática para AITrack Monitor System*
