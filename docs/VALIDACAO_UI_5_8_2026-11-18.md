# Validação — UI-5.8: níveis de autonomia

**Executada em:** 18/11/2026 03:49 (`America/Sao_Paulo`)  
**Etapa:** 31 de 74  
**Checkpoint anterior:** `f336e8d`  
**Commit de implementação:** `bc5523e`

## Resultado esperado

Separar observar, recomendar, solicitar aprovação e executar, aplicando um teto
de risco à autonomia e impedindo que decisão da IA seja confundida com ação feita.

## Resultado obtido

- Cada versão de configuração possui uma política imutável com um dos níveis
  `observe`, `recommend`, `approval` ou `execute`.
- `observe` produz somente observação; `recommend` preserva recomendação;
  `approval` exige aprovação; `execute` apenas declara elegibilidade.
- O nível `execute` exige allowlist de tipos e teto `low` ou `medium`. Risco
  `high`/`critical`, revisão pedida pela decisão, ação fora da allowlist ou marcada
  para aprovação resulta em `approval_required`.
- `notify_authorities` e `request_vehicle_command` nunca podem integrar a
  allowlist autônoma.
- Configuração sem política não pode ser ativada. Política só nasce enquanto a
  configuração está `draft` e não pode ser alterada nem excluída.
- Cada decisão concluída passa a persistir a política, o nível e a autorização
  detalhada de cada ação.

## Evidências

- Migration `037_create_agent_autonomy_policies.sql` aplicada e repetida com
  **0 migrations pendentes**.
- Prova MariaDB rejeitou update/delete da política e inclusão depois da ativação,
  todas com SQLSTATE `45000`.
- `contact_owner` de risco baixo, explicitamente permitido, ficou
  `execution_eligible`; o mesmo caso com risco crítico ficou
  `approval_required` por risco e revisão humana.
- A autorização foi persistida junto da decisão e relida como `execute`/
  `execution_eligible`.
- Rollback confirmou **zero configurações, políticas, execuções e decisões
  sintéticas residuais**.
- **11 testes específicos de autonomia** e **407 testes backend** aprovados;
  12 integrações opt-in puladas.

## Limitações e segurança

- `execution_eligible` não significa executada. Ainda não existe worker nem canal
  externo nesta etapa.
- Mensagem, ligação e comando deverão passar novamente pelas políticas da fila,
  consentimento, horário, custo, idempotência e recibos das etapas de ação.
- Nenhuma configuração foi ativada e nenhum modelo externo foi chamado.

## Conclusão

**Aprovada.** A independência dos agentes agora é graduada e fail-closed, com
teto de risco, menor privilégio e autorização reconstruível por decisão.
