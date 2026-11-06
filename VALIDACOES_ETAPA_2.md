# Validações — Etapa 2: Incidentes reais

## UI-2.1 — Migration de incidentes

**Data:** 06/11/2026
**Checkpoint anterior:** `68cf40d`

### Contrato implementado

- Incidente separado de evento técnico.
- Identidade obrigatória por `tracker.veiculo_unificado`.
- Monitor opcional, preservando o incidente se o monitor for removido.
- Correlação única para idempotência por veículo/agente/episódio.
- Estados: novo, triagem, atendimento, aguardando resposta, escalado,
  resolvido e encerrado.
- Severidade, risco, fonte, responsável, SLA, posição, hipótese, confiança e
  resolução persistentes.
- Campo `version` preparado para concorrência otimista.
- Nenhuma timeline ou regra de transição embutida nesta migration; entram nas
  tarefas UI-2.2 e UI-2.4.

### Evidências

- Migration somente aditiva e restrita ao schema `tracker`.
- Estrutura e índices conferidos no banco.
- Inserção de prova desfeita com rollback, sem incidente residual.
- Suíte backend e compilação Python sem regressão.
- Testes específicos: `4 passed`.
- Suíte completa do backend: `36 passed`.
- Compilação dos módulos Python: sem erros.
- Tabela criada com 36 colunas, chave primária, correlação única e seis índices
  operacionais adicionais.
- FKs confirmadas para `veiculo_unificado` e `monitores`.
- Reaplicação idempotente concluída sem alteração destrutiva.
- Correlação duplicada bloqueada pelo banco.
- Prova transacional desfeita: 0 registros residuais.

A migration `007_create_incidents.sql` foi aplicada diretamente porque o runner
descrito no handoff ainda não existe. O número `005` permanece reservado para
os índices de eventos definidos no plano original.

## UI-2.2 — Timeline auditável do incidente

**Data:** 06/11/2026
**Checkpoint anterior:** `b649580`

### Contrato implementado

- Histórico separado e append-only por incidente.
- Ordem determinística por ocorrência e ID.
- Chave de idempotência obrigatória para impedir entradas repetidas.
- Ator humano, agente, sistema ou integração identificado.
- Mudança de estado anterior/novo, resumo e detalhes estruturados.
- Vínculo opcional com evento técnico e evidência externa.
- IDs de correlação e causalidade para rastrear automações.
- Visibilidade interna ou para o cliente.
- Remover um evento técnico preserva a timeline; remover em cascata um
  incidente não foi habilitado.

### Evidências

- Migration aditiva e restrita ao schema `tracker`.
- FKs, índices e idempotência conferidos no banco.
- Incidente e entrada de prova desfeitos na mesma transação.
- Nenhum registro artificial residual.
- Suíte backend e compilação Python sem regressão.
- Testes específicos: `4 passed`.
- Suíte completa do backend: `40 passed`.
- Compilação dos módulos Python: sem erros.
- Tabela criada com 19 colunas, chave primária, idempotência única e quatro
  índices operacionais adicionais.
- FK do incidente confirmada como `RESTRICT`; FK do evento como `SET NULL`.
- Reaplicação idempotente concluída.
- Segunda entrada com a mesma chave foi bloqueada.
- Rollback conjunto: 0 incidentes e 0 entradas residuais.

A migration `008_create_incident_timeline.sql` foi aplicada diretamente no
schema `tracker`; o runner de migrations documentado no handoff continua
pendente.

## UI-2.3 — API de listagem e detalhe

**Data:** 06/11/2026
**Checkpoint anterior:** `f2cbbab`

### Contrato implementado

- `GET /api/incidents`: filtros por estado, severidade, fonte, veículo,
  monitor, responsável e somente abertos.
- Paginação por `limit`/`offset`, limitada a 200 itens por resposta.
- `GET /api/incidents/{id}`: incidente enriquecido com identidade, monitor e
  timeline cronológica.
- Timeline limitada a 1.000 entradas e sinalização de truncamento.
- Queries dinâmicas usam somente colunas permitidas e valores parametrizados.
- Datas, decimais, booleanos e JSON possuem serialização estável.
- Erros de validação, ausência e indisponibilidade têm códigos distintos sem
  expor detalhes internos.

### Evidências

- Testes de filtros, limites, detalhe, 404, falha e serialização.
- Suíte backend e compilação Python sem regressão.
- Endpoints reais respondem sobre as tabelas operacionais vazias.
- Testes específicos da API: `7 passed`.
- Suíte completa do backend: `47 passed`.
- Compilação dos módulos Python: sem erros.
- `GET /api/incidents`: HTTP 200 em 76,7 ms, contrato
  `incident-list.v1`, total 0.
- Lista somente aberta: HTTP 200 em 36,8 ms.
- Estado inválido: HTTP 400 com `INVALID_INCIDENT_FILTER`.
- ID inexistente: HTTP 404 com `INCIDENT_NOT_FOUND`.
- Limite de timeline acima do máximo: HTTP 400.
- Regressão de identidade: `/api/v1/vehicles` HTTP 200.
- Reinício sem exceções e API/socket ativos nas portas 5009/9000.

## UI-2.4 — Máquina de estados dos incidentes

**Data:** 06/11/2026
**Checkpoint anterior:** `2948d33`

### Contrato implementado

- Estados operacionais: novo, triagem, em atendimento, aguardando resposta,
  escalado, resolvido e encerrado.
- Comandos explícitos substituem alterações livres de `status`: encaminhar para
  triagem, iniciar atendimento, aguardar resposta, escalar, retomar, resolver,
  encerrar e reabrir.
- Transições ilegais são recusadas antes de acessar o banco.
- Iniciar atendimento exige responsável humano ou agente.
- Aguardar resposta exige data da próxima ação.
- Resolver exige código e justificativa; falso positivo exige classificação
  coerente. Encerrar exige resolução prévia.
- Cada transição altera incidente e acrescenta timeline na mesma transação.
- `version` implementa concorrência otimista e impede atualização sobre estado
  obsoleto.
- `idempotency_key` torna repetição segura e devolve o estado atual sem gerar
  nova entrada.
- Ator, resumo, correlação e limites do schema são validados antes do SQL.
- O serviço é interno nesta etapa. Os comandos HTTP orientados ao operador
  serão expostos em UI-2.7/UI-2.8, junto das respectivas regras de autorização;
  não foi criado um endpoint genérico de escrita sem autenticação.

### Evidências

- Testes focais da máquina: `18 passed`.
- Suíte completa do backend: `65 passed`.
- Compilação dos módulos Python: sem erros.
- Prova no MariaDB percorreu
  `new → triage → in_progress → waiting_response → escalated → resolved → closed`.
- Estado final real: `closed`, versão 7 e seis entradas auditáveis na timeline.
- Repetição da primeira chave retornou replay idempotente e não criou entrada.
- Versão obsoleta foi bloqueada por `IncidentConflict`.
- Transição inválida `closed → close` foi bloqueada por `InvalidTransition`.
- Toda a prova foi desfeita com rollback; uma segunda conexão confirmou zero
  incidentes e zero entradas de timeline residuais.

### Limite deliberado

UI-2.4 garante o núcleo transacional usado por humanos e agentes. Autenticação,
autorização e comandos públicos não pertencem à máquina em si. A API de leitura
de UI-2.3 permanece inalterada; reconhecer, assumir, comentar, resolver e marcar
falso positivo entram em UI-2.7/UI-2.8.

## UI-2.5 — Correlação de episódios com incidentes

**Data:** 06/11/2026
**Checkpoint anterior:** `43f40b4`

### Contrato implementado

- Todo episódio comportamental Tracker persistido passa pelo correlacionador na
  mesma transação do evento e do score.
- A identidade operacional sempre é resolvida em
  `tracker.veiculo_unificado`; eventos sem identidade não abrem incidente.
- A chave `vehicle_id + correlation_group` é independente da fonte. Tracker e
  Dirija Bem podem anexar episódios diferentes ao mesmo incidente.
- Na ausência de `correlation_group`, o `episode_id` é usado como agrupamento.
- A primeira evidência cria o incidente e as seguintes atualizam severidade,
  risco, fonte e quantidade de eventos.
- Fontes distintas convertem `primary_source` para `fused`.
- Cada evidência gera timeline auditável com fonte, registro de origem,
  episódio, tipo, severidade e horário observado.
- Repetir a mesma evidência não incrementa contadores nem duplica timeline.
- Chaves acima dos limites do schema recebem hash SHA-256 determinístico.
- Cada evidência nova incrementa `version`, preservando o controle de
  concorrência da máquina de estados.
- Falha inesperada na correlação desfaz evento, score e incidente juntos.

### Evidências

- Testes focais do correlacionador, motor e máquina de estados: `43 passed`.
- Suíte completa do backend: `74 passed`.
- Compilação dos módulos Python: sem erros.
- Prova no MariaDB associou uma evidência Tracker e uma evidência Dirija Bem,
  com `episode_id` distintos, ao mesmo `correlation_group` e `vehicle_id`.
- Resultado real: um incidente, fonte `fused`, severidade `critical`, risco
  30, duas evidências e dois atores de integração.
- Replays Tracker e Dirija Bem não criaram timeline nem incrementaram
  `event_count`.
- Toda a prova foi desfeita; segunda conexão confirmou zero incidentes,
  identidades temporárias e eventos residuais.

### Limite explícito

O Tracker já chama o correlacionador automaticamente ao persistir episódios.
O contrato Dirija Bem (`source`, `codusu`, `source_record_id`, `episode_id` e
`correlation_group`) está implementado e foi validado no banco, mas o consumidor
contínuo que transforma métricas/viagens do banco Dirija Bem em episódios ainda
pertence à etapa específica de integração dessa fonte. Até lá, não se afirma que
toda viagem Dirija Bem abre incidentes automaticamente.

## UI-2.6 — Fila real de incidentes no lugar de alertas mock

**Data:** 06/11/2026
**Checkpoint anterior:** `a335110`

### Contrato implementado

- A antiga aba Alertas foi renomeada para Incidentes e agora contém uma fila
  operacional alimentada por `GET /api/incidents`.
- O filtro inicial mostra somente incidentes abertos; operador pode consultar
  todos ou selecionar cada estado real da máquina.
- Filtros de estado e severidade são enviados ao backend, em vez de aplicados
  sobre uma lista local fictícia.
- Cabeçalho calcula contagens apenas a partir da resposta real e deixa explícito
  quando são itens carregados/consultados.
- Lista mostra identidade veicular, fonte Tracker/Dirija Bem/fundida, severidade,
  estado, evidências e abertura.
- Selecionar um item consulta `GET /api/incidents/{id}` e exibe timeline
  auditável, risco, monitor, responsável e fonte.
- Carregamento, erro, retry e ausência de dados possuem estados explícitos.
- Falha de API nunca faz fallback para conteúdo demonstrativo.
- Botões falsos de reconhecer/resolver foram removidos. A interface explica que
  ações persistentes entram em UI-2.7 e UI-2.8.
- O arquivo `mockData/mockAlerts.ts`, com oito alertas inventados, foi removido.

### Evidências

- Testes do frontend: `42 passed` em 12 suítes.
- Regressão completa do backend: `74 passed`.
- Checagem TypeScript `npx tsc --noEmit`: sem erros.
- Build otimizado CRA: compilado com sucesso.
- Playwright/Chrome abriu `http://localhost:3003`, navegou para Alertas e
  confirmou o contrato visual contra o backend real.
- Banco/API sem incidentes exibiu “Fila sem incidentes”, sem criar exemplos.
- Aviso “DADOS NÃO OPERACIONAIS” e títulos do mock antigo não estavam no DOM.
- Filtro inicial `open` confirmado e console do navegador sem erros.
- Backend permaneceu ativo nas portas 5009/9000; frontend ativo na 3003.

### Limite deliberado

A fila é somente leitura nesta tarefa. Isso evita reaproveitar endpoints antigos
de `monitor_alertas` ou simular sucesso local. Reconhecer, assumir e comentar
serão comandos reais de incidente em UI-2.7; resolução e falso positivo, em
UI-2.8.
