# Validação UI-7.7 — relatórios por fonte

**Data:** 25/11/2026 01:00 (`America/Sao_Paulo`)

**Checkpoint:** `0dd1311` · **Implementação:** `458d7ea`

## Resultado

Relatórios podem ser gerados em modo Tracker, Dirija Bem ou unificado. Cada run
congela período, fuso, fontes, definição e fórmula. A visão unificada soma contagens,
distância e tempo e recalcula taxas pelos totais, preservando `source_breakdown`.
A interface apresenta ID público e proveniência. O mesmo pedido/ator é idempotente.

## Evidências

- migration 059 aplicada/idempotente;
- teste ponderado: 12 eventos / 120 km = 10 eventos/100 km e 4 eventos/h;
- prova MariaDB criou exatamente um run, repetiu o mesmo ID, bloqueou `UPDATE` por
  trigger e deixou zero resíduo após rollback;
- 7 testes focados, 518 backend, 86 frontend, TypeScript e build aprovados.

## Limitações

Download e agendamento pertencem à UI-7.9. Entrega externa fica bloqueada até
autenticação e papéis das UI-8.1/UI-8.2.
