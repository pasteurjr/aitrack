# Validação — UI-6.5: eventos do provedor de mensagens

**Executada em:** 19/11/2026 23:08 (`America/Sao_Paulo`)
**Etapa:** 43 de 74
**Checkpoint anterior:** `e2e2437`
**Commit de implementação:** `1395cb4`

## Resultado esperado

Persistir entrega, leitura e resposta com timestamps e conteúdo sanitizado.

## Resultado obtido

Webhook autenticado por HMAC normaliza estados do provedor, deduplica cada
evento e mantém estado desconhecido explícito. Eventos fora de ordem nunca
regridem a ação. Somente metadados allowlisted são persistidos; telefone, corpo
e token ficam apenas no hash do payload.

## Evidências

- Migration 046 aplicada e reaplicação sem pendências.
- Prova MariaDB vinculou evento a ação/recibo, bloqueou exclusão e confirmou
  rollback sem resíduos.
- Matriz cobriu sete famílias de status, fuso obrigatório, sanitização e HMAC.
- **18 testes focados** e **446 testes backend** passaram; 12 opt-in pulados.

## Limitações

- A composição visual no incidente pertence à UI-6.9.
- A prova usou callback sintético assinado; nenhum provedor real foi acionado.

## Conclusão

**Aprovada.** Entrega, leitura, resposta e falha possuem registro durável,
idempotente e sanitizado.
