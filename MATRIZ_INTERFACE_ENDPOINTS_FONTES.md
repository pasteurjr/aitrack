# Matriz da Interface, Endpoints, Fontes e Modos Operacionais

**Sistema:** AITrack + DataDrivr  
**Data de referência:** 06/11/2026  
**Frontend:** `aitrackdatadrivr/frontend`  
**Backend:** `aitrackdatadrivr/server`  
**Base configurável:** `REACT_APP_API_BASE_URL`  
**Objetivo:** deixar explícito o que cada tela consulta, de onde o dado vem, se há efeito colateral e se a informação é operacional, simulada ou mock.

---

## 1. Como ler esta matriz

### Fonte

Indica onde o backend obtém a informação:

- **Tracker DB:** banco `tracker` no MariaDB compartilhado;
- **Dirija Bem DB:** banco `dirijabem`, consultado em modo leitura pela aplicação;
- **Memória do motor:** estruturas do `behavioral_engine` dentro do processo atual do backend;
- **Monitor DB:** tabelas de monitores no banco `tracker`;
- **Mock frontend:** arquivo TypeScript local, sem consulta ao backend;
- **Configuração:** variável de ambiente definida no build do frontend.

### Modo operacional

Indica como o dado foi produzido:

- **live:** originado de fluxo atual de telemetria;
- **simulation:** gerado pelos simuladores do projeto;
- **replay:** reprodução de dados históricos;
- **mock:** exemplo fixo compilado junto com a interface;
- **indeterminado:** a API não fornece metadados suficientes para distinguir os modos anteriores.

### Situação

| Símbolo | Significado |
|---|---|
| ✅ | Integração real, com ressalvas documentadas |
| ⚠️ | Integração parcial, ambígua ou dependente de estado volátil |
| 🧪 | Conteúdo demonstrativo/mock |
| ⛔ | Capacidade ainda inexistente |

> Regra operacional: consultar um banco real não prova que o dado seja de produção. Um simulador também pode gravar no banco real. A procedência precisa viajar junto com cada registro.

---

## 2. Matriz executiva por tela

| Tela/área | Componente principal | Dados apresentados | Fonte atual | Modo identificável? | Situação |
|---|---|---|---|---|---:|
| Cabeçalho | `OperationModeBadge` | Ambiente global | `REACT_APP_OPERATION_MODE` | Sim, mas apenas no nível do build | ✅ |
| Dashboard | `BehavioralDashboard` | veículos, usuários, scores e KPIs | Tracker DB, lista fixa Dirija Bem e memória do motor | Não por registro | ⚠️ |
| Contexto do veículo | `VehicleDetailHeader` | identidade, fonte, modo e última comunicação | cadastro unificado | Sim, conforme metadados disponíveis | ✅ |
| Mapa | `MapComponent` | posições, scores, eventos, trilha e rota | Tracker DB, Dirija Bem DB e memória | Não por registro | ⚠️ |
| Timeline | `EventsTimeline` | episódios comportamentais recentes | motor reidratado de `tracker.eventos` | Não | ✅ |
| Análises | `VehicleAnalytics` | scores, distribuição e rankings | memória do motor | Não | ⚠️ |
| Lista de monitores | `MonitorDashboard` | monitores e vínculos | Monitor DB | Não aplicável ao cadastro | ✅ |
| Veículos do monitor | `MonitorDashboard` | veículo, score, eventos e estado | Monitor DB + memória do motor | Não | ⚠️ |
| Detalhe visual do monitor | `MonitorDetailView` | analisadores e eventos | mock frontend | Sim: faixa DEMONSTRAÇÃO | 🧪 |
| Alertas | `AlertsPanel` | alertas, IA, recomendações e ações | mock frontend | Sim: faixa DEMONSTRAÇÃO | 🧪 |
| Catálogo de eventos | `EventsCatalog` | tipos, estatísticas e SLA | mock frontend | Sim: faixa DEMONSTRAÇÃO | 🧪 |
| Cercas | inexistente | desenho, regras e violações | — | — | ⛔ |
| Sensores/comandos | inexistente | capacidades, leituras e comandos | — | — | ⛔ |
| Incidentes | inexistente | caso operacional e atendimento | — | — | ⛔ |
| Runtime dos agentes | inexistente | decisão, ferramentas e memória | — | — | ⛔ |
| Comunicações | inexistente | mensagens, ligações e recibos | — | — | ⛔ |

---

## 3. Dashboard

### 3.1 Seleção Tracker

| Item | Valor atual |
|---|---|
| Componente | `BehavioralDashboard.tsx` |
| Serviço | `trackerService.getPositions()` |
| Endpoint | `GET /api/posicoes` |
| Backend | `server/api.py::get_latest_positions` |
| Fonte | tabelas `tracker.localizacao` e `tracker.veiculos` |
| Filtro | última posição por veículo, comunicada nos últimos 10 minutos |
| Atualização | a cada 5 segundos |
| Efeito colateral | nenhum |
| Limitação | resposta não informa se o pacote veio de rastreador físico ou simulador |
| Situação | ⚠️ real, com procedência ambígua |

O seletor apresenta placa e `device_id`. O endpoint lê o banco real, mas o simulador Tracker grava no mesmo fluxo. Portanto, o modo não pode ser inferido apenas pela tabela.

### 3.2 Seleção Dirija Bem

| Item | Valor atual |
|---|---|
| Serviço | `dirijabemService.getUsers()` |
| Endpoint | `GET /api/dirijabem/users` |
| Fonte real | constante `USERS` em `server/dirijabem_api.py` |
| Banco consultado | nenhum neste endpoint |
| Atualização | uma vez ao abrir o componente |
| Situação | ⚠️ lista fixa apresentada por API |

A lista parece dinâmica, mas contém dez usuários escritos no código do backend. Ela não representa automaticamente os usuários ativos ou autorizados do banco Dirija Bem.

### 3.3 Selecionar usuário Dirija Bem

| Item | Valor atual |
|---|---|
| Serviço | `dirijabemService.startUserTrip(userId)` |
| Endpoint | `POST /api/dirijabem/user/{codusu}/start` |
| Backend | gerenciador de replay em memória |
| Efeito colateral | inicia ou retoma uma viagem/replay |
| Situação | ⚠️ ação escondida atrás de uma seleção |

Selecionar um usuário não é uma operação somente leitura. A interface inicia processamento no backend. O comportamento deve ser separado em um botão explícito, com confirmação do modo.

### 3.4 KPIs e rankings

| Dado | Serviço | Endpoint | Fonte | Atualização | Situação |
|---|---|---|---|---:|---:|
| score médio | `fleetService.getStats()` | `GET /api/fleet/stats` | memória do motor | 3 s | ⚠️ |
| eventos do dia | `fleetService.getStats()` | `GET /api/fleet/stats` | memória do motor | 3 s | ⚠️ |
| quantidade de veículos | `fleetService.getStats()` | `GET /api/fleet/stats` | memória do motor | 3 s | ⚠️ |
| top/bottom 3 | `fleetService.getStats()` | `GET /api/fleet/stats` | memória do motor | 3 s | ⚠️ |
| scores individuais | `fleetService.getScores()` | `GET /api/fleet/scores` | memória do motor | 3 s | ⚠️ |

O estado é perdido quando o backend reinicia. Os KPIs também não informam origem, modo, janela ou versão da regra usada no cálculo.

### 3.5 Frota unificada por fonte

| Item | Comportamento atual |
|---|---|
| Componente | `UnifiedFleetPanel.tsx` |
| Serviço | `unifiedVehicleService.getAll()` |
| Endpoint | `GET /api/v1/vehicles` |
| Visões | Todos, Tracker e Dirija Bem |
| Identidade | tabela `tracker.veiculo_unificado`, contrato `vehicle.v1` |
| Pesquisa | nome, placa, `device_id` e `codusu`, ignorando acentos e caixa |
| Tracker | identidade versionada; score complementado pelo motor em memória quando disponível |
| Dirija Bem | identidade versionada; score permanece indisponível |
| Identificação | badge e cor específicos por fonte |
| Score Tracker | exibido somente quando existe no motor |
| Score Dirija Bem | `Score indisponível`; nenhum valor é inventado |
| Seleção Tracker | limpa a seleção Dirija Bem e centraliza o veículo |
| Seleção Dirija Bem | limpa a seleção Tracker e consulta viagem já ativa |
| Efeito colateral | a visão unificada não chama `POST /start` |

Os seletores específicos foram preservados. O seletor Dirija Bem antigo ainda inicia replay; a lista unificada é somente seleção/consulta e torna a origem visível em cada item.

---

## 4. Mapa

### 4.1 Cabeçalho de contexto do veículo

Ao selecionar um item da frota unificada, `VehicleDetailHeader.tsx` resolve a
identidade pelo `GET /api/v1/vehicles` e mantém acima do mapa o nome, placa,
identificadores Tracker/Dirija Bem, procedência, modo, última comunicação e
estado cadastral. Ausências e falhas são explícitas; o componente não cria
score, horário ou vínculo. Fechar o cabeçalho limpa as seleções e o filtro de
eventos do veículo.

| Função | Serviço | Endpoint | Fonte | Frequência/gatilho | Situação |
|---|---|---|---|---|---:|
| veículos visíveis | `trackerService.getPositions()` | `GET /api/posicoes` | Tracker DB | 3 s | ⚠️ |
| cor/score do marcador | `fleetService.getScores()` | `GET /api/fleet/scores` | memória | 3 s | ⚠️ |
| eventos no mapa | `fleetService.getEvents(20)` | `GET /api/fleet/events?limit=20` | memória | 3 s | ⚠️ |
| eventos da Timeline | `fleetService.getEvents(50)` | `GET /api/fleet/events?limit=50` | memória | ao destacar evento | ⚠️ |
| trilha incremental Tracker | `positionService.getLatest()` | `GET /api/positions/latest/{VEICOD}` | Tracker DB | 5 s | ✅ |
| rota Dirija Bem | `dirijabemService.getUserRoute()` | `GET /api/dirijabem/user/{codusu}/route` | Dirija Bem DB | troca de usuário | ⚠️ |
| último ponto Dirija Bem | `dirijabemService.getUserLastPoint()` | `GET /api/dirijabem/user/{codusu}/last-point` | Dirija Bem DB | 5 s | ⚠️ |

### Limitações relevantes

- o marcador usa score padrão `85` quando não encontra score para um `device_id`; esse segundo fallback ainda precisa ser removido;
- posição e score chegam em requisições separadas e sem identificador de snapshot;
- rota Dirija Bem representa a viagem ativa, que pode ser replay, sintética ou contínua;
- a resposta não inclui `mode`, `source`, `received_at`, `source_at` ou qualidade GPS;
- o mapa não possui cercas, rotas autorizadas, sensores ou incidentes.

---

## 5. Timeline

| Item | Valor atual |
|---|---|
| Componente | `EventsTimeline.tsx` |
| Serviço | `fleetService.getEvents(50)` |
| Endpoint | `GET /api/fleet/events?limit=50` |
| Fonte | motor em memória reidratado de `tracker.eventos` no startup |
| Atualização | 5 segundos |
| Persistência | eventos e score persistidos; janela ativa restaurada no startup |
| Detectores reais | aceleração, frenagem, curva brusca e excesso de velocidade |
| Filtros | veículo, tipo, severidade e período, combináveis |
| Drill-down | episódio completo → coordenadas exatas no mapa + contexto do veículo |
| Modo | indeterminado |
| Estado de falha | explícito, com nova tentativa e aviso de dado desatualizado |
| Situação | ⚠️ real e volátil |

Os eventos comportamentais trabalham como episódios desde a UI-1.5 e a
timeline deduplica por `episode_id`. A seleção entrega o episódio completo ao
mapa, evitando que polling ou filtros apontem para outra posição. A tela ainda
não trabalha com incidentes operacionais.

---

## 6. Análises

| Item | Valor atual |
|---|---|
| Componente | `VehicleAnalytics.tsx` |
| Endpoints | `GET /api/fleet/scores` e `GET /api/fleet/events?limit=100` |
| Fonte | memória do motor |
| Atualização | 5 segundos, em conjunto |
| Consistência | as duas respostas não compartilham versão/snapshot |
| Estado de falha | mantém última resposta válida com aviso |
| Situação | ⚠️ cálculo real sobre estado volátil |

Não há consulta direta das métricas históricas do Dirija Bem nesta tela. O nome “AITrack + DataDrivr” não significa que todos os gráficos combinem as duas fontes.

---

## 7. Monitores AI

### 7.1 Lista e configuração

| Função | Serviço | Endpoint | Fonte | Situação |
|---|---|---|---|---:|
| listar monitores | `monitorService.getAll()` | `GET /api/monitors` | tabelas do Monitor DB | ✅ |
| detalhe cadastral | `monitorService.getById()` | `GET /api/monitors/{id}` | Monitor DB | ✅ |
| veículos vinculados | `monitorService.getVehicles()` | `GET /api/monitors/{id}/vehicles` | Monitor DB + memória | ⚠️ |

O endpoint de veículos enriquece os vínculos persistidos com score e eventos do processo atual. Se o motor estiver indisponível, retorna HTTP 503; não inventa mais `85/0/OK`.

### 7.2 Detalhe visual

| Item | Estado atual |
|---|---|
| veículos entregues pelo `App.tsx` | `mockVehiclesInMonitors` |
| eventos | `mockEvents` |
| catálogo usado para ícones | `eventTypesCatalog` mock |
| resultado produzido por IA | nenhum |
| aviso visível | `DEMONSTRAÇÃO — DADOS NÃO OPERACIONAIS` |
| Situação | 🧪 mock explícito |

A lista lateral consulta dados reais, mas a área principal do detalhe ainda é demonstrativa. Essa separação precisa ser preservada até o detalhe consumir uma API real.

---

## 8. Alertas

| Item | Estado atual |
|---|---|
| componente | `AlertsPanel.tsx` |
| alertas | `mockAlerts` |
| estatísticas | `mockAlertStats` |
| análise de IA | texto fixo mock |
| reconhecer/resolver | `window.alert`, sem persistência |
| chamadas HTTP durante uso | nenhuma |
| aviso visível | `DEMONSTRAÇÃO — DADOS NÃO OPERACIONAIS` |
| Situação | 🧪 mock explícito |

O backend possui endpoints de alertas, mas esta tela ainda não os utiliza:

- `GET /api/alerts`;
- `GET /api/alerts/{id}`;
- `PUT /api/alerts/{id}/acknowledge`;
- `PUT /api/alerts/{id}/resolve`;
- `PUT /api/alerts/{id}/dismiss`;
- `GET /api/alerts/stats`.

A existência do endpoint não prova que o fluxo autônomo esteja implementado. Não há runtime de IA, fila de ações ou integração de comunicação.

---

## 9. Catálogo de Eventos

| Item | Estado atual |
|---|---|
| componente | `EventsCatalog.tsx` |
| tipos | `eventTypesCatalog` mock |
| estatísticas | `mockEventStats` |
| chamadas HTTP durante uso | nenhuma |
| aviso visível | `DEMONSTRAÇÃO — DADOS NÃO OPERACIONAIS` |
| Situação | 🧪 mock explícito |

O backend oferece `GET /api/events/catalog` e `GET /api/events/stats`, mas o frontend não os consome. O catálogo mock inclui capacidades sem detector ou sensor comprovado.

---

## 10. Endpoints utilizados atualmente pelo frontend

| Método | Endpoint | Serviço central | Consumidor | Leitura/escrita | Fonte |
|---|---|---|---|---|---|
| GET | `/api/posicoes` | `trackerService` | Dashboard, mapa, `VehicleList` | leitura | Tracker DB |
| GET | `/api/positions/latest/{id}` | `positionService` | mapa | leitura | Tracker DB |
| GET | `/api/fleet/scores` | `fleetService` | Dashboard, mapa, Análises | leitura | memória |
| GET | `/api/fleet/events` | `fleetService` | Timeline, mapa, Análises | leitura | memória |
| GET | `/api/fleet/stats` | `fleetService` | Dashboard | leitura | memória |
| GET | `/api/dirijabem/users` | `dirijabemService` | Dashboard, `VehicleList` | leitura | lista fixa |
| POST | `/api/dirijabem/user/{id}/start` | `dirijabemService` | Dashboard, `VehicleList` | **ação** | replay manager |
| GET | `/api/dirijabem/user/{id}/route` | `dirijabemService` | mapa | leitura | Dirija Bem DB |
| GET | `/api/dirijabem/user/{id}/last-point` | `dirijabemService` | mapa | leitura | Dirija Bem DB |
| GET | `/api/monitors` | `monitorService` | Monitores | leitura | Monitor DB |
| GET | `/api/monitors/{id}` | `monitorService` | Monitores | leitura | Monitor DB |
| GET | `/api/monitors/{id}/vehicles` | `monitorService` | Monitores | leitura | Monitor DB + memória |
| GET | `/api/v1/vehicles` | `unifiedVehicleService` | frota unificada e cabeçalho do veículo | leitura | `veiculo_unificado` |

---

## 11. Serviços disponíveis, mas ainda não ligados às telas

| Serviço frontend | Endpoints preparados | Observação |
|---|---|---|
| `alertService` | alertas, detalhe, reconhecer, resolver, descartar e estatísticas | `AlertsPanel` continua mock |
| `eventService` | catálogo, eventos persistidos e estatísticas | `EventsCatalog` continua mock |
| `vehicleService` | adicionar/remover veículo de monitor | não há controles na interface |
| `monitorService` | criar, editar, alternar e análises | a tela só consulta lista/detalhe/veículos |
| `fleetService.getVehicleScore` | score individual | não utilizado diretamente |

Esses serviços representam contratos disponíveis, não funcionalidades concluídas.

### API versionada de identidade

`GET /api/v1/vehicles` expõe o contrato `vehicle.v1` com identidade, procedência, modo e última comunicação. A frota unificada do Dashboard consome esse endpoint desde a UI-1.3 e o cabeçalho contextual desde a UI-1.4; os seletores legados continuam temporariamente separados.

---

## 12. Metadados que precisam entrar nos contratos

Toda resposta operacional de telemetria, evento, score ou incidente deverá incluir, quando aplicável:

| Campo | Finalidade |
|---|---|
| `source` | `tracker`, `dirijabem` ou integração futura |
| `mode` | `live`, `simulation`, `replay` ou `synthetic` |
| `source_at` | horário produzido pela fonte |
| `received_at` | horário recebido pelo AITrack |
| `processed_at` | horário processado pelo detector/agente |
| `source_record_id` | rastreabilidade até o registro original |
| `correlation_id` | correlação entre posição, evento, incidente e ação |
| `quality` | validade, precisão e completude |
| `is_stale` | indicação explícita de dado vencido |
| `detector_version` | regra/modelo que produziu o evento |

O indicador global de ambiente deve continuar existindo, mas não substitui esses campos por registro.

---

## 13. Regras para evolução da interface

1. Toda tela nova deve declarar seu endpoint, fonte e modo nesta matriz.
2. Componentes não podem importar Axios nem possuir endereço de backend; o teste `apiBoundary.test.ts` fiscaliza essa regra.
3. Qualquer `POST`, `PUT` ou `DELETE` precisa ser apresentado como ação explícita, nunca escondido em seleção ou navegação.
4. Mock deve permanecer com faixa de demonstração até ser removido do código.
5. Falha não pode ser substituída por valor plausível.
6. Dado preservado após falha precisa mostrar que está desatualizado.
7. Endpoint real não deve ser chamado de integração concluída sem fluxo de ponta a ponta e teste operacional.
8. Dados Tracker e Dirija Bem devem conservar origem e identidade ao serem unificados.
9. Ações de agente precisam registrar decisão, política, ferramenta, resultado e correlação.
10. A matriz deve ser atualizada no mesmo commit que altera a origem de uma tela.

---

## 14. Próximas correções derivadas da matriz

| Prioridade | Correção | Motivo |
|---:|---|---|
| P0 | remover score padrão `85` do mapa | ainda mascara score ausente |
| P0 | adicionar `source` e `mode` às respostas | banco real não distingue simulador/replay |
| P0 | separar seleção Dirija Bem da ação de iniciar replay | leitura não deve provocar mutação escondida |
| P0 | persistir eventos e scores | estado em memória desaparece no reinício |
| P1 | ligar Alertas a incidentes reais | tela atual é mock |
| P1 | ligar Catálogo à capacidade real dos protocolos | catálogo atual promete recursos inexistentes |
| P1 | substituir detalhe do monitor por execuções reais | área principal ainda usa mocks |
| P1 | incluir saúde/frescor por fonte | operador precisa distinguir offline de falha sistêmica |

---

## 15. Critério de aceite desta matriz

A matriz foi conferida contra:

- `src/App.tsx`;
- componentes das seis opções do menu;
- `src/services/apiService.ts`;
- rotas Flask em `server/api.py`, `server/dirijabem_api.py` e `server/monitor_api.py`;
- camada `server/monitor_db.py`;
- arquivos mock importados pelo frontend.

Ela descreve o estado atual do código no commit imediatamente posterior a `fa885d4`. Mudanças futuras de fonte, endpoint, modo ou efeito colateral deverão atualizar este documento.
