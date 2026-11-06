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
