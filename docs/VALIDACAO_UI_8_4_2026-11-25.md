# Validação UI-8.4 — auditoria consultável

**Data:** 25/11/2026 10:43 (`America/Sao_Paulo`)

**Checkpoint:** `37c2f22` · **Implementação:** `9c18090`

## Resultado esperado

Mudanças críticas devem registrar, na mesma transação, quem fez o quê, estado anterior
e posterior, motivo e correlação. A consulta deve respeitar tenant/permissão e a trilha
não pode ser alterada nem expor segredos.

## Resultado obtido

- `audit_events` é append-only e indexada por tenant, tempo, recurso, ator e correlação;
- writer participa da conexão/transação do domínio;
- transições de incidente e criação/edição/arquivamento de cercas gravam antes/depois;
- API protegida filtra por período, ator, ação, recurso e correlação com cursor estável;
- redação recursiva cobre credenciais, contatos, áudio, transcrição e prompts.

## Evidências

- migration 065 aplicada e registrada;
- prova MariaDB: evento visível dentro da transação, valor sensível ausente, tentativa de
  UPDATE rejeitada pelo trigger e `rollback_residue = 0`;
- 50 testes focados aprovados;
- regressão: **554 aprovados, 12 ignorados**.

## Limitação registrada

As timelines históricas especializadas continuam válidas e não foram apagadas. Os
demais módulos legados serão conectados ao writer transversal conforme forem alterados;
isso evita reescrever artificialmente eventos passados sem evidência original.
