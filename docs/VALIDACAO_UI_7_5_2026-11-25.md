# Validação UI-7.5 — período e comparação analítica

**Data:** 25/11/2026 00:53 (`America/Sao_Paulo`)

**Checkpoint:** `abb96ef` (00:49:45 -03) · **Implementação:** `c27b3ec`

## Esperado e obtido

Esperado: comparar janelas equivalentes sem misturar fontes ou limites temporais.

Obtido: contrato `behavior-analytics.v1` normaliza datas locais/offset para UTC,
consulta `[from,to)`, limita a 366 dias e aceita período anterior ou comparação
customizada de duração idêntica. Tracker e Dirija Bem permanecem discriminados em
totais, tipos e veículos. A tela passou a consultar esse histórico e mostra filtros,
fuso e comparação, removendo scores voláteis e o corte arbitrário de 100 eventos.

## Evidências

- 5 testes focados de fuso, duração, fontes e API;
- 511 testes backend e 86 frontend aprovados;
- TypeScript e build de produção aprovados;
- consulta real de 24 h e período anterior retornou zero de forma explícita, sem
  fallback nem dados inventados;
- `EXPLAIN`: acesso `range` pela chave `idx_timestamp`;
- nenhuma migration ou escrita foi necessária.

## Limitação

Os números desta etapa são contagens brutas persistidas. Distância, horas de
condução, cobertura e taxas normalizadas pertencem à UI-7.6.
