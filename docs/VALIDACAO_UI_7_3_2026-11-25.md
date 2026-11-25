# Validação UI-7.3 — desvio e parada não planejada

**Data:** 25/11/2026 00:43 (`America/Sao_Paulo`)

**Checkpoint anterior:** `5dc45e8` (criado às 00:38:48 -03)

**Implementação:** `e39c61c`

## Escopo e resultado esperado

Detectar desvio de uma rota atribuída sem reagir a uma única leitura ruidosa e
detectar parada não planejada somente depois da permanência mínima. A avaliação
deveria preservar a versão da rota usada na execução, aceitar a incerteza do GPS,
excluir paradas cadastradas e ser idempotente.

## Resultado obtido

- estado por execução persistido em `monitoramento.route_execution_states`;
- distância até a `LineString` calculada em metros contra o corredor congelado;
- acurácia do pacote amplia a tolerância e faixa de histerese evita oscilação na borda;
- desvio e recuperação exigem duas amostras consecutivas;
- parada abaixo de 2 km/h abre episódio após 300 segundos, exceto dentro do raio de parada prevista;
- episódios ativos são únicos por execução/tipo e podem terminar como `recovered`;
- recibo `(execução, fonte, posição externa)` impede processamento repetido;
- posição mais antiga que a última processada é ignorada;
- ingestão Tracker resolve a identidade unificada e avalia somente execuções ativas;
- falha do detector fica isolada e não invalida a posição já gravada.

## Evidências executadas

1. `python migrations/apply.py --dry-run`: **0 migrations pendentes** após a 056.
2. Testes focados: **3 passed**.
3. Regressão do backend: **499 passed, 12 skipped** em 2,33 s.
4. Prova MariaDB em transação controlada:
   - sequência observada: `recovered → deviation → recovered`;
   - parada observada: `unplanned_stop → recover_stop`;
   - episódios finais: um desvio recuperado e uma parada recuperada;
   - 9 posições distintas produziram 9 recibos;
   - repetição do último identificador retornou `idempotent_replay=true`;
   - rollback final: **0 rotas/resíduos** da validação.
5. `git diff --check`: sem erro de whitespace.

## Limitações e segurança

- Nesta etapa, o hook de ingestão está ligado ao Tracker. A posição Dirija Bem
  será consumida quando passar pelo adaptador operacional unificado, sem escrita
  no banco `dirijabem`.
- Nenhum incidente ou alerta externo é disparado diretamente pelo detector; os
  episódios persistidos serão correlacionados pela automação em etapa própria.
- A prova usou somente tabelas do banco `monitoramento`, dentro de uma transação
  revertida. Nenhum dado real foi alterado.
