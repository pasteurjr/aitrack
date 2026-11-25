# Validação UI-8.5 — integrações e saúde

**Data:** 25/11/2026 10:49 (`America/Sao_Paulo`)

**Checkpoint:** `c0d70b0` · **Implementação:** `857da87`

## Resultado esperado

Tracker, Dirija Bem, IA, canais, banco e workers devem expor estado, último sucesso/falha,
atraso e histórico, sem revelar topologia ou segredos ao público.

## Resultado obtido

- `/api/health/live` informa apenas processo vivo;
- `/api/health/ready` é público e mínimo, retornando 503 quando fonte/componente crítico
  está desconhecido ou em outage;
- `/api/health/integrations` exige `health.read` e retorna nove componentes e transições;
- Tracker/Dirija Bem usam `integration_health` como fonte consistente tanto no painel quanto
  no readiness;
- painel Saúde atualiza a cada 30 s e apresenta loading, erro/retry, vazio e sucesso.

## Evidências

- migration 066 aplicada;
- ensaio transacional: `ai_provider → degraded`, transição registrada, token redigido e rollback;
- revisão tester independente encontrou divergência readiness/painel e lacunas de redação;
  ambas foram corrigidas antes do commit;
- **559 backend**, **93 frontend**, TypeScript e build de produção aprovados.

## Limitação registrada

Os campos de profundidade/idade de fila existem, mas não são agregados globalmente no
endpoint para evitar vazamento de volume entre empresas. A instrumentação UI-8.6 deve
publicar gauges sem labels de alta cardinalidade e com escopo seguro.
