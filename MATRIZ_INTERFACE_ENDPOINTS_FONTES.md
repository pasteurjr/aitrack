# Matriz da interface, endpoints, fontes e modos operacionais

**Sistema:** AITrack + DataDrivr  
**Atualizada em:** 17/11/2026 11:20 (`America/Sao_Paulo`)
**Frontend:** `aitrackdatadrivr/frontend`  
**Backend:** `aitrackdatadrivr/server`  
**Base da API:** `REACT_APP_API_BASE_URL` → `src/config/api.ts`
**Objetivo:** declarar, para cada bloco visual, endpoint, fonte, modo, efeito colateral e comportamento em erro.

## 1. Regras de interpretação

- **Fonte** é o sistema ou armazenamento consultado pelo backend.
- **Modo** é a proveniência operacional: `production`, `simulation`, `replay`, `mixed` ou `unconfirmed` no selo global; registros de identidade usam `live`, `simulation`, `replay`, `synthetic` ou `unknown`.
- Banco persistente não implica produção: os simuladores também gravam nos bancos integrados.
- Falha de API nunca pode virar valor plausível. A tela deve mostrar erro ou dado anterior marcado como desatualizado.
- Não há conteúdo mockado nas telas de produção. Fixtures dos testes não são dados de runtime.

## 2. Matriz executiva das telas atuais

| Tela/bloco | Componente | Endpoint(s) principal(is) | Fonte | Modo/proveniência | Erro/vazio | Situação |
|---|---|---|---|---|---|---|
| Selo global | `OperationModeBadge` | `GET /api/runtime/environment` | configuração do processo ativo | Autoritativo por Tracker e Dirija Bem; produção exige ambas `live` | falha ou snapshot vencido → `NÃO CONFIRMADO` e ações reais bloqueadas | Operacional |
| Frota/seleção | `BehavioralDashboard`, `UnifiedFleetPanel` | `GET /api/posicoes`, `/api/dirijabem/users`, `/api/v1/vehicles` | Tracker, Dirija Bem e identidade em `monitoramento` | origem preservada por identidade; seletores legados têm ressalvas | `AsyncDataState`; nenhum veículo inventado | Operacional com legado |
| Contexto selecionado | `VehicleDetailHeader` | `GET /api/v1/vehicles` | identidade operacional unificada | `source`, `mode`, identificadores e última comunicação | ausência/falha explícita | Operacional |
| KPIs comportamentais | `BehavioralDashboard` | `GET /api/fleet/stats`, `/api/fleet/scores` | motor comportamental reidratado/persistência de eventos | modo global; score não carrega modo próprio | mantém último snapshot apenas com aviso `stale` | Operacional com limitação |
| Mapa e rota | `MapComponent` | posições, scores, eventos, posição Tracker, rota/último ponto Dirija Bem | Tracker + Dirija Bem + motor | origem vem da seleção; snapshots não são atômicos | erros parciais registrados; nenhuma posição fabricada | Operacional com limitação |
| Cercas no mapa | `GeofenceLiveLayer`, `GeofenceDesigner` | `/api/geofences*` | schema unificado `monitoramento` | comum às duas fontes; alvo identifica veículo/motorista/grupo | preserva snapshot antigo com aviso; vazio explícito no editor | Operacional |
| Timeline | `EventsTimeline` | `GET /api/fleet/events` | eventos comportamentais reidratados de `tracker.eventos` | origem explícita e filtrável; modo ainda não viaja em cada evento | erro/retry, vazio e `stale` compartilhados | Operacional com limitação |
| Análises | `VehicleAnalytics` | `/api/fleet/scores`, `/api/fleet/events` | motor comportamental | predominantemente Tracker; Dirija Bem não compõe todos os gráficos | erro/vazio/stale compartilhados | Operacional com limitação |
| Monitores | `MonitorDashboard` | `/api/monitors`, `/{id}`, `/{id}/vehicles` | `monitoramento.monitores`, alvos e motor | alvo conserva `tipo_veiculo`; lista não implica LLM | 503 comportamental aparece explicitamente; retry/voltar | Operacional por regras |
| Detalhe do monitor | `MonitorDetailView` | `/api/monitors/{id}/vehicles`, `/api/events` | alvos operacionais + eventos persistidos | filtro por `device_id`; origem vem do evento/identidade quando disponível | erro explícito; zero eventos por categoria | Operacional |
| Incidentes | `AlertsPanel` | `/api/incidents*`, `/api/v1/vehicles` | `monitoramento.incidents` e `incident_timeline` | Tracker/Dirija Bem preservados pela identidade operacional | erro/retry e vazio; conflito de versão explícito | Operacional |
| Catálogo de eventos | `EventsCatalog` | `/api/events/catalog`, `/api/events/stats` | `tracker.tipo_evento` e eventos persistidos | capacidade indica detecção ativa/planejada, não modo | erro/retry e vazio | Operacional |
| Sensores/comandos | inexistente | — | — | — | — | Pendente (etapas 12–23) |
| Runtime autônomo de IA | inexistente | — | — | — | — | Pendente (etapas 24–38) |
| Mensagens/voz | inexistente | — | — | — | — | Pendente (etapas 39–52) |

## 3. Cabeçalho e modo operacional

| Campo | Contrato atual |
|---|---|
| Serviço | `runtimeEnvironmentService.getCurrent()` |
| Endpoint | `GET /api/runtime/environment` |
| Autoridade | backend em execução, sem cache |
| Fontes declaradas | Tracker e Dirija Bem |
| Atualização | polling de 15 segundos |
| Estados | produção, simulação, replay, misto e não confirmado |
| Regra segura | erro, ausência, conflito, timestamp inválido ou idade acima de 30 s → não confirmado |

O antigo `REACT_APP_OPERATION_MODE` não é mais autoridade da interface.

## 4. Dashboard e identidade

| Função | Serviço | Endpoint | Fonte | Efeito colateral |
|---|---|---|---|---|
| posições Tracker | `trackerService.getPositions` | `GET /api/posicoes` | `tracker.localizacao` + `tracker.veiculos` | nenhum |
| usuários Dirija Bem legado | `dirijabemService.getUsers` | `GET /api/dirijabem/users` | lista exposta pelo backend | nenhum |
| iniciar viagem/replay legado | `dirijabemService.startUserTrip` | `POST /api/dirijabem/user/{id}/start` | gerenciador de replay | **inicia/retoma processamento** |
| identidade unificada | `unifiedVehicleService.getAll` | `GET /api/v1/vehicles` | `monitoramento.veiculos`, identidades e vínculos; fallback legado controlado | nenhum |
| KPIs | `fleetService.getStats` | `GET /api/fleet/stats` | motor comportamental | nenhum |
| scores | `fleetService.getScores` | `GET /api/fleet/scores` | motor comportamental | nenhum |

O painel unificado não chama o `POST /start`; a seleção Dirija Bem legada ainda possui esse efeito e deve ser tratada como replay, não como simples leitura.

## 5. Mapa, eventos e análises

| Função | Endpoint | Fonte | Atualização/limitação |
|---|---|---|---|
| marcadores Tracker | `GET /api/posicoes` | Tracker | polling; origem física versus simulador depende do modo global |
| score do marcador | `GET /api/fleet/scores` | motor | requisição separada da posição; score ausente ainda usa fallback visual `85` no mapa, risco registrado |
| eventos do mapa/timeline | `GET /api/fleet/events` | memória reidratada de `tracker.eventos` | episódios reais com `source`; modo por evento ainda ausente |
| posição incremental | `GET /api/positions/latest/{veicod}` | Tracker | polling de 5 s |
| rota Dirija Bem | `GET /api/dirijabem/user/{id}/route` | Dirija Bem | viagem ativa, que pode ser sintética/replay |
| último ponto Dirija Bem | `GET /api/dirijabem/user/{id}/last-point` | Dirija Bem | polling de 5 s |
| catálogo persistido | `GET /api/events/catalog` | `tracker.tipo_evento` | distingue detecção ativa de planejada |
| estatísticas persistidas | `GET /api/events/stats` | `tracker.eventos` | agregação do período atual |

## 6. Monitores e detalhe

| Função | Endpoint | Fonte | Observação de verdade |
|---|---|---|---|
| listar/detalhar | `GET /api/monitors`, `GET /api/monitors/{id}` | `monitoramento.monitores` | cadastro operacional, não prova uso de LLM |
| alvos e estado | `GET /api/monitors/{id}/vehicles` | `monitoramento.monitor_targets` + motor | falha comportamental retorna 503; não existe fallback 85/0/ok |
| eventos do detalhe | `GET /api/events?device_id=...` | eventos persistidos | sem veículo selecionado, consulta todos os alvos do monitor |
| análises disponíveis no cliente | `GET /api/monitors/{id}/analyses` | `monitoramento.monitor_analises` | serviço existe; a UI atual ainda não apresenta runtime autônomo completo |
| criar/editar/toggle | `POST/PUT /api/monitors*` | monitoramento | serviços disponíveis; controles completos pertencem ao bloco de agentes |

## 7. Incidentes operacionais

| Ação | Endpoint | Escrita | Evidência persistida |
|---|---|---:|---|
| listar/detalhar | `GET /api/incidents`, `GET /api/incidents/{id}` | não | incidente, identidade e timeline |
| reconhecer | `POST /api/incidents/{id}/acknowledge` | sim | ator, versão e chave idempotente |
| assumir | `POST /api/incidents/{id}/assume` | sim | operador responsável e timeline |
| comentar | `POST /api/incidents/{id}/comments` | sim | comentário auditável |
| resolver | `POST /api/incidents/{id}/resolve` | sim | classificação e resolução |
| falso positivo | `POST /api/incidents/{id}/false-positive` | sim | taxonomia e evidência |
| falso negativo | `POST /api/incidents/false-negatives` | sim | novo registro correlacionado |

O nome histórico `AlertsPanel` não significa que a tela use alertas mock: ela hoje representa a fila real de incidentes.

## 8. Cercas eletrônicas

| Função | Endpoint | Fonte | Situação |
|---|---|---|---|
| listar/criar | `GET/POST /api/geofences` | `monitoramento.geofences` + versões | operacional |
| editar/arquivar | `PUT/DELETE /api/geofences/{ref}` | versões e auditoria | concorrência otimista/arquivamento seguro |
| opções/vínculos | `/assignment-options`, `/{ref}/assignments` | identidades, grupos, agendas | operacional |
| criar grupo | `POST /api/geofences/monitoring-groups` | grupos e membros | operacional |
| estado ao vivo | `GET /api/geofences/live-state` | cerca, atribuição, último estado e episódio | polling de 5 s; limite 200 |

Círculos e polígonos são comuns a Tracker e Dirija Bem. Violação de cerca gera incidente, mas não equivale, sozinha, a confirmação de roubo.

## 9. Serviços presentes, mas sem fluxo completo na UI

| Serviço | Contratos existentes | Limitação atual |
|---|---|---|
| `alertService` | `/api/alerts*` | legado; a tela principal usa incidentes |
| `monitorService` | criação, edição, toggle e análises | configuração/runtime autônomo ainda incompletos |
| `vehicleService` | adicionar/remover alvo do monitor | controles completos ainda não expostos |
| `fleetService.getVehicleScore` | score individual | sem consumidor direto |

Disponibilidade no cliente não significa entrega de ponta a ponta.

## 10. Campos de proveniência exigidos na evolução

| Campo | Finalidade |
|---|---|
| `source` | Tracker, Dirija Bem ou integração futura |
| `mode` | live, simulation, replay ou synthetic |
| `source_at` / `received_at` / `processed_at` | separar relógios da origem, ingestão e processamento |
| `source_record_id` | voltar ao registro de origem |
| `correlation_id` | ligar posição, evento, incidente, decisão e ação |
| `quality` / `is_stale` | validade, precisão, completude e frescor |
| `detector_version` | regra/modelo responsável pelo evento |

## 11. Regras obrigatórias para novas telas

1. Registrar nesta matriz endpoint, fonte, modo, efeito colateral e comportamento em falha.
2. Usar serviços de `apiService.ts`; componentes não podem importar Axios, usar `fetch` nem conter URL/IP.
3. Apresentar `POST`, `PUT` e `DELETE` como ações explícitas.
4. Nunca substituir falha por valor plausível.
5. Marcar snapshot preservado após falha como desatualizado.
6. Conservar a origem Tracker/Dirija Bem em listas, detalhes, eventos, incidentes e relatórios.
7. Não chamar monitor baseado em regras de “agente autônomo com IA”.
8. Registrar decisão, política, ferramenta, tentativa e resultado de qualquer ação futura do agente.

## 12. Validação desta versão

Conferida contra:

- as seis abas declaradas em `src/App.tsx`;
- consumidores em `src/components/`;
- todos os serviços em `src/services/apiService.ts`;
- blueprints de runtime, veículos, monitores, eventos, incidentes e cercas;
- consultas atuais aos schemas `tracker`, `dirijabem` e `monitoramento`.

Comandos de apoio:

```bash
rg -n "apiClient\.(get|post|put|delete)" aitrackdatadrivr/frontend/src/services/apiService.ts
rg -n "Service\." aitrackdatadrivr/frontend/src/components --glob '*.tsx'
rg -n "Blueprint|@.*route" aitrackdatadrivr/server --glob '*.py'
```

Principais riscos ainda explícitos: score visual `85` no mapa quando ausente; ação de replay escondida no seletor legado Dirija Bem; modo ainda não acompanha cada evento/posição; relatórios, sensores, agente autônomo e comunicações permanecem pendentes.
