# Validação UI-7.9 — exportação e agendamento

**Data:** 25/11/2026 01:08 (`America/Sao_Paulo`)

**Checkpoint:** `3c050a9` · **Implementação:** `179e53e`

## Resultado

CSV e JSON são derivados do mesmo relatório rastreável e preservam filtros, fontes,
período e fórmula. Células iniciadas por `=`, `+`, `-` ou `@` recebem prefixo seguro.
Cada exportação registra job/evento, hash SHA-256, tamanho, linhas, ator e snapshot de
permissão interna. A UI faz download local. Agendas diária/semanal calculam próximo
horário com fuso, mas são salvas como `blocked_auth`, sem `next_run_at` executável.

## Evidências

- migration 061 aplicada/idempotente;
- 6 testes focados; 525 backend e 86 frontend; TypeScript/build aprovados;
- prova transacional gerou CSV unificado com 2 linhas, um job e um evento;
- replay manteve job/hash; trigger bloqueou mutação;
- agenda semanal BRT calculou próxima execução e permaneceu bloqueada;
- rollback deixou zero job e zero agenda de validação.

## Limitação de segurança

Worker recorrente e entrega externa não foram ativados. Eles dependem de identidade
autenticada e autorização por papel, previstas nas UI-8.1 e UI-8.2.
