# Validação R4 — falsos positivos e falsos negativos

**Data:** 26/11/2026 (`America/Sao_Paulo`)

**Checkpoint antes da etapa:** `5a39921`

**Escopo:** avaliação local, offline, de 17 cenários sintéticos versionados do Tracker e Dirija Bem. Não houve leitura/escrita no banco nem alteração de credenciais.

## Resultado esperado

Calcular matriz de confusão e FPR/FNR com intervalos de confiança de 95%, estratificados por fonte, classe de evento, severidade e contexto. Um score não deve ser tratado como gatilho único quando houver falsos negativos relevantes.

## Resultado obtido

- 17 cenários: TP=3, FP=0, FN=7, TN=7.
- FNR global: **70% (7/10)**; IC 95% Wilson: **39,68%–89,22%**.
- FPR global: **0% (0/7)**; IC 95%: **0%–35,43%**. Zero observados nesta amostra pequena não demonstra ausência de falsos positivos.
- Tracker: FNR **75% (3/4)**; IC 95% **30,06%–95,44%**.
- Dirija Bem: FNR **66,67% (4/6)**; IC 95% **30%–90,32%**.
- Severidade alta: FNR **80% (4/5)**. Crítica: **60% (3/5)**.
- Classes de autonomia bloqueadas no resultado: `harsh_brake`, `speeding` e `mixed`.
- Erro absoluto do cálculo do score contra os valores de referência: zero. Isso valida a fórmula do score, mas a fórmula ainda falha como classificador de intervenção no limite 70.

Os sete falsos negativos estão enumerados e revisados tecnicamente na evidência JSON. Em todos, o cenário rotulado para intervenção mantém score acima de 70. A recomendação permanece: **não usar score como gatilho único**; preservar detectores independentes por evento e revisão humana para alto/crítico.

## Validação executada

`python -m pytest -q tests/test_score_evaluation.py tests/test_agent_evaluation.py` — **7 passaram**. Nenhum teste acessou o banco ou chamou serviços externos.

## Limites e decisão

Os casos são sintéticos e têm apenas 17 observações; os intervalos são amplos. Rótulos precisam de revisão independente pela operação antes de qualquer ajuste de pesos ou uso para autonomia. O arquivo `agent_cases_v1.json` tem decisões candidatas estáticas que ecoam respostas preparadas; sua taxa perfeita não mede LLM nem agente em execução e não foi usada como evidência de desempenho.

**Resultado da etapa:** medição concluída e critério de segurança **reprovado**. Nenhum peso ou limite foi ajustado. A reprovação bloqueia autonomia baseada apenas no score, mas não impede testar em R5 as barreiras determinísticas em modo simulado.

**Evidência:** `docs/evidence/UI_R4_SYNTHETIC_SCORE_EVALUATION_2026-11-26.json`.
