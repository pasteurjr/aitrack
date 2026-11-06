# Validações — Etapa 1: Eventos e Identidade

## UI-1.2 — Procedência, modo e última comunicação

**Data:** 06/11/2026
**Checkpoint anterior:** `2960557`

### Validações automatizadas

- Backend: `22 passed`.
- Frontend: `29 passed`.
- TypeScript: sem erros.
- Build de produção: concluído sem warnings de código.

### Validação operacional

O backend foi reiniciado e `GET /api/v1/vehicles` foi consultado contra o banco atual, somente leitura:

| Verificação | Resultado |
|---|---:|
| contrato | `vehicle.v1` |
| veículos | 20 |
| `tracker_only` | 10 |
| `app_only` | 10 |
| fonte Tracker | 10 |
| fonte Dirija Bem | 10 |
| modo `unknown` | 20 |
| última comunicação `null` | 20 |

O resultado `unknown`/`null` é intencional e seguro: as fontes atuais ainda não fornecem modo e última comunicação ao cadastro unificado. O endpoint não presume produção, simulação ou horário inexistente. Os modos poderão ser configurados por `AITRACK_TRACKER_MODE` e `AITRACK_DIRIJABEM_MODE`; horários serão preenchidos quando os adaptadores de fonte entregarem essa informação.

### Compatibilidade

- Novo endpoint aditivo: `GET /api/v1/vehicles`.
- APIs legadas não foram alteradas.
- App 1 não foi migrado nem afetado.

## UI-1.3 — Lista unificada pesquisável

**Data:** 06/11/2026
**Checkpoint anterior:** `e170bab`

### Validações automatizadas

- Frontend: `30 passed`.
- TypeScript: sem erros.
- Build de produção: concluído com sucesso.
- Testes cobrem filtro por fonte, pesquisa, resultado vazio e seleção.

### Validação operacional com Playwright

| Verificação | Resultado |
|---|---:|
| endpoint `GET /api/v1/vehicles` | HTTP 200 |
| total exibido | 20 |
| pesquisa utilizada | `614` |
| itens visíveis após pesquisa | 1 |
| erros de página | 0 |

A lista passou a consumir a identidade versionada. A pesquisa encontra placa, nome, `device_id` e `codusu`; modo e última comunicação são apresentados explicitamente, inclusive quando `unknown`/`null`.

## UI-1.4 — Cabeçalho contextual do veículo

**Data:** 06/11/2026
**Checkpoint anterior:** `0f93f4c`

### Validações automatizadas

- Frontend: `35 passed` em 11 suítes.
- Testes novos: ausência de seleção, identidade Tracker, identidade sem vínculo, fechamento e falha da API.
- TypeScript: `npx tsc --noEmit` sem erros.
- Build de produção: concluído com sucesso.
- `git diff --check`: sem erros de whitespace.

### Validação operacional com navegador automatizado

| Verificação | Resultado |
|---|---:|
| frontend | HTTP 200 |
| pesquisa utilizada | `SIM-1000` |
| itens visíveis após pesquisa | 1 |
| identidade resolvida | Veículo simulado rastreador GPS 1 |
| procedência | `TRACKER` |
| modo retornado | `unknown` |
| último contato retornado | não informado |
| cabeçalho após fechar | removido |
| erros de página | 0 |
| requisições falhas | 0 |

O cabeçalho usa o mesmo contrato versionado da frota unificada e fica acima do
mapa durante a seleção. Nenhum score, modo ou horário ausente é fabricado. A
captura da prova visual foi gerada em
`/tmp/aitrack-ui-1.4-vehicle-header.png` durante a validação local.

## UI-1.5 — Episódio de excesso de velocidade

**Data:** 06/11/2026
**Checkpoint anterior:** `562a313`

### Contrato implementado

- O episódio inicia no primeiro pacote acima de 80 km/h.
- Pacotes seguintes acima do limite não criam novos eventos.
- O detector rearma somente abaixo de 75 km/h.
- Cada início recebe `episode_id` determinístico e `episode_state: started`.
- Estado independente por veículo e protegido por lock.
- Persistência no banco ocorre fora do lock do motor.

### Evidências

- Teste de condição contínua: um único evento.
- Teste de recuperação abaixo de 75 km/h: novo episódio permitido.
- Teste na fronteira de 75 km/h: detector permanece armado e não duplica.
- Teste focal: `8 passed`.
- Suíte completa do backend: `24 passed`.
- Compilação dos módulos Python: sem erros.
- O `.venv` descrito no handoff ainda não existe; nenhum pacote foi instalado
  no Python global e a suíte foi executada com o interpretador já configurado.

## UI-1.6 — Cooldown e histerese dos demais detectores

**Data:** 06/11/2026
**Checkpoint anterior:** `a9a229f`

### Contrato implementado

- Aceleração, frenagem e curva brusca emitem um evento por episódio.
- Liberação exige queda para 60% do limiar de ativação.
- Novo episódio só pode ser emitido após cooldown configurável, padrão 30 s.
- Estado e cooldown são independentes por veículo e tipo de detector.
- Eventos recebem `episode_id` e `episode_state: started`.

### Evidências

- Condição sustentada não duplica evento.
- Liberação seguida de reativação rápida é suprimida.
- Liberação após cooldown permite novo episódio.
- Os três detectores transitórios carregam os metadados do episódio.
- Teste focal do motor: `11 passed`.
- Suíte completa do backend: `27 passed`.
- Compilação dos módulos Python: sem erros.

## UI-1.7 — Persistência de eventos e scores essenciais

**Data:** 06/11/2026
**Checkpoint anterior:** `34b841e`

### Contrato implementado

- Evento e snapshot do score são gravados na mesma transação.
- `tracker.behavioral_scores` mantém score, janela, quantidade de eventos e
  instante do cálculo por `device_id`.
- No startup, o backend restaura snapshots e eventos da última hora antes de
  iniciar socket, API e replay Dirija Bem.
- Eventos restaurados recompõem o score e o estado dos detectores.
- IDs persistidos impedem duplicação se a restauração for chamada novamente.
- Falha de restauração não impede o backend de subir e fica explícita no log.

### Validações automatizadas

- Teste focal do motor: `13 passed`.
- Suíte completa do backend: `29 passed`.
- Compilação dos módulos Python: sem erros.
- Teste unitário confirmou `INSERT eventos` e `UPSERT behavioral_scores` em
  um único commit.
- Teste de reidratação confirmou evento, score, detector e idempotência.

### Validação do banco `tracker`

| Verificação | Resultado |
|---|---:|
| migration | somente `CREATE TABLE IF NOT EXISTS` |
| tabela anterior | inexistente |
| tabela criada | `tracker.behavioral_scores` |
| colunas | 7 |
| índices | `PRIMARY` + 2 secundários |
| prova transacional com rollback | 0 registros residuais |
| restauração isolada | 114,2 ms |

A migration `006_create_behavioral_scores.sql` foi aplicada diretamente porque
o runner descrito no handoff ainda não existe. O número `005` continua reservado
para os índices da tabela de eventos previstos no plano.

### Validação operacional após reinício

| Verificação | Resultado |
|---|---:|
| restauração no startup | 0 scores e 0 eventos disponíveis na janela atual |
| API | porta 5009 ativa |
| socket Tracker | porta 9000 ativa |
| `/api/fleet/scores` | HTTP 200 |
| `/api/fleet/events?limit=5` | HTTP 200 |
| `/api/v1/vehicles` | HTTP 200, 20 veículos |
| `/api/unified/vehicles` | HTTP 200, 20 veículos |
| erros no log | 0 |

## UI-1.8 — Contadores e scores por episódio

**Data:** 06/11/2026
**Checkpoint anterior:** `e638fee`

### Contrato implementado

- `episode_id` é a unidade de penalização e contagem.
- Duplicatas do mesmo episódio são ignoradas no score, contador diário e
  retorno da timeline.
- `events_today` considera somente episódios cuja ocorrência é do dia atual.
- Eventos legados sem `episode_id` permanecem individuais.

### Evidências

- Episódio duplicado aplica uma única penalidade.
- Episódio duplicado conta uma única vez no dia.
- Evento do dia anterior não entra em `events_today`.
- Eventos legados continuam compatíveis.
- Teste focal do motor: `16 passed`.
- Suíte completa do backend: `32 passed`.
- Compilação dos módulos Python: sem erros.
- Após reinício: `/api/fleet/stats`, `/api/fleet/scores` e
  `/api/fleet/events?limit=50` responderam HTTP 200.
- Sem simuladores ativos, o contrato retornou legitimamente 0 veículos e 0
  episódios, sem criar valores de demonstração.

## UI-1.9 — Filtros da timeline

**Data:** 06/11/2026
**Checkpoint anterior:** `9c2ce2b`

### Contrato implementado

- Filtros combináveis por veículo, tipo, severidade e período.
- Contador de episódios visíveis sobre os 50 mais recentes consultados.
- Estado vazio específico quando os filtros não encontram resultado.
- Limpeza de todos os filtros em uma ação.
- Seleção filtrada preserva o índice original até a migração por identidade da
  UI-1.10.

### Evidências

- Filtros de veículo, tipo e severidade combinados.
- Período de uma hora exclui episódio antigo.
- Limpeza restaura todos os resultados.
- Clique em resultado filtrado mantém o índice original.
- Frontend: `38 passed` em 11 suítes.
- TypeScript: sem erros.
- Build de produção: concluído com sucesso.
- Navegador: filtro combinado reduziu 3 episódios a 1 (`SIM-1001`).
- Navegador: período de uma hora exibiu 2 de 3 episódios.
- Ação acessível do episódio encontrada exatamente uma vez.
- Erros de página: 0.
- Dados da validação visual foram interceptados no navegador; nenhum evento
  artificial foi escrito no banco.
- Captura: `/tmp/aitrack-ui-1.9-timeline-filters.png`.
