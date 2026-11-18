# Validação — UI-5.2: persistência de execuções e decisões

**Executada em:** 18/11/2026 03:21 (`America/Sao_Paulo`)  
**Etapa:** 25 de 74  
**Checkpoint anterior:** `f21f876`  
**Commit de implementação:** `f3ded1c`

## Resultado esperado

Cada execução de agente deve registrar entrada, contexto, versão, saída, latência,
custo, erro e correlação, permitindo reconstrução independente do provedor.

## Resultado obtido

- `agent_runs` vincula a execução à identidade e à versão exata da configuração,
  preservando provedor/modelo usados no momento da fila.
- Entrada e contexto são snapshots JSON; incidente, veículo, causa, tentativa,
  gatilho, chave idempotente e correlação ficam explícitos.
- Conclusão guarda saída, tokens de entrada/saída, custo em USD, latência e erro
  normalizado, além dos relógios de fila/início/fim.
- Decisão fica em tabela própria, uma por execução, com versão de formato. Isso evita
  confundir texto bruto do provedor com a decisão operacional.
- Estados finais (`succeeded`, `failed`, `timed_out`, `cancelled`) não podem ser
  reabertos e uma decisão registrada não pode ser alterada ou excluída.
- O módulo oferece criação idempotente e conclusão com versão otimista; a API desta
  etapa é somente leitura para inspeção do ledger.

## Evidências

- Migration `033_create_agent_execution_ledger.sql` aplicada; nova execução:
  **0 migrations pendentes**.
- Prova transacional persistiu:
  - sucesso com 120 tokens de entrada, 30 de saída, US$ 0,012345, 850 ms, saída e
    decisão `unstructured.v1`;
  - falha com 30.100 ms, `provider_timeout` e mensagem sintética.
- Ambas preservaram `synthetic-provider`, `synthetic-model` e correlação
  `incident-ui52`.
- Triggers bloquearam reabrir a execução final e alterar a decisão com SQLSTATE
  `45000`; rollback confirmou **zero execuções sintéticas residuais**.
- Runtime reiniciado: `/api/agent-runs` respondeu HTTP 200,
  `schema_version=agent-runs.v1`, `count=0`; banco confirmou zero runs reais.
- **8 testes específicos** e **352 testes backend** aprovados; 12 integrações opt-in
  puladas.

## Limitações e segurança

- Nenhuma configuração de agente está ativa, portanto não existe execução real nem
  custo externo. Os valores da prova foram sintéticos e revertidos.
- O formato de decisão ainda é genérico `unstructured.v1`; a etapa 5.3 criará e
  validará o contrato estruturado antes de um provedor ser integrado.
- A API não expõe criação/conclusão ao navegador; esses métodos são internos para o
  futuro worker, reduzindo superfície de falsificação.
- Política de retenção e anonimização será definida nas etapas de governança.

## Conclusão

**Aprovada.** O sistema já possui memória auditável para cada futura inferência,
inclusive falhas e custos, sem afirmar que um modelo esteja em execução hoje.
