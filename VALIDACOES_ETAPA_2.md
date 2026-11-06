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
