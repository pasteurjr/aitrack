# Validação UI-8.3 — isolamento por empresa

**Data:** 25/11/2026 10:41 (`America/Sao_Paulo`)

**Checkpoint:** `fa548b4` · **Implementação:** `568dd13`

## Resultado esperado

O tenant deve vir exclusivamente da sessão. Listas, detalhes e mutações não podem
revelar nem alterar recurso pertencente a outra empresa, inclusive quando o ID é conhecido.

## Resultado obtido

- migration 064 atribui tenant às raízes de incidentes, cercas, rotas, agentes e relatórios;
- vínculo de fonte é exclusivo por `source_code + external_type + external_value` para
  Tracker e Dirija Bem;
- incidentes, cercas e rotas filtram consultas e locks de mutação pelo tenant da sessão;
- atores de comandos de incidente e cerca são reconstruídos da sessão, ignorando autoria
  declarada pelo cliente;
- acesso cruzado retorna ausência do recurso, sem revelar sua existência.

## Evidências

- migration aplicada e registrada; todas as 9.574 ocorrências, 2 cercas, 5 agentes e
  1 definição de relatório possuem tenant; não há raiz histórica nula;
- ensaio transacional: o mesmo incidente resultou em `0` para tenant B e `1` para o
  proprietário; rollback deixou `0` tenants de prova;
- 53 testes focados aprovados;
- regressão backend: **551 aprovados, 12 ignorados**, sem falhas.

## Limitações e operação segura

O banco possuía uma única empresa, portanto o backfill foi determinístico para
`migration-default`. Uma nova empresa deve cadastrar os vínculos Tracker/Dirija Bem antes
de liberar ingestão. Processos internos sem requisição HTTP usam o proprietário persistido;
tenant recebido de payload público nunca é fonte de autoridade.
