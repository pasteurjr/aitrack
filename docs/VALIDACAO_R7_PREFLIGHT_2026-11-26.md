# R7 — preflight técnico local de operação e recuperação

**Data:** 26/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 7 de 8 — em andamento  
**Checkpoint pré-etapa:** `295800f`  
**Ambiente:** harness determinístico local; SQLite temporário; nenhum serviço externo ou banco compartilhado acessado.

## Objetivo esperado

Preparar e exercitar playbooks, restart, rollback, backup/restauração e reconciliação em homologação, com dois operadores e um supervisor; medir RTO/RPO contra metas aprovadas; provar ausência de perda e duplicação.

## Resultado deste preflight

- `python3 scripts/validate_operational_playbooks.py`: 8/8 cenários passaram: incidente, falso positivo, guarda de classificação, falha da fonte, fallback de IA, takeover, conflito entre operadores e zero efeitos externos.
- `python3 scripts/validate_runbook.py`: zero achados estáticos.
- `PYTHONPATH=. pytest -q tests/test_safe_load_test.py tests/test_operational_playbooks.py tests/test_runbook.py`: **5 passaram**.
- `python3 scripts/run_safe_load_test.py --iterations 2000 --workers 4`: harness SQLite temporário passou. Antes/depois do fechamento/reabertura: 2.000 receipts, 2.000 incidentes e 2.000 ações; perdas 0; duplicações 0; 100/100 leases vencidos recuperados; RTO sintético 0,0067 s; throughput 993,67/s.
- A primeira chamada de pytest sem `PYTHONPATH=.` falhou na coleta porque o pacote `scripts` não estava no caminho. Repetida com `PYTHONPATH=.` passou. Não é falha do produto.

## Resultado esperado versus obtido

| Item | Esperado | Obtido |
|---|---|---|
| Playbooks técnicos | Todos os cenários sem efeitos externos | 8/8 passaram; mensagens, chamadas de voz e comandos físicos = 0 |
| Validador do runbook | Nenhum comando perigoso ou tópico obrigatório ausente | Zero achados |
| Persistência/restart | Sem perda/duplicação após reinício e retomada de leases | SQLite temporário fechou/reabriu; 2.000 linhas por entidade, perda/duplicação zero, 100 leases recuperados |
| Backup e restauração | Backup verificável restaurado em homologação | Não executado |
| Serviço e rollback | Restart/rollback por supervisor em homologação | Não executado |
| Exercício humano | 2 operadores e 1 supervisor, sem ajuda do autor | Não executado |
| Metas | RTO/RPO formalmente aprovados | Não localizadas metas aprovadas; resultado sintético não as substitui |

## Evidência

`docs/evidence/UI_R7_LOCAL_RECOVERY_2026-11-26.json`. O ensaio anterior de 5.000 registros no SQLite também permanece em `docs/VALIDACAO_UI_8_7_2026-11-25.md`; ambos validam apenas o harness local.

## Decisão e pendências para concluir R7

R7 **não está concluída**. O runbook declara que backup/restauração dependem do DBA e aprovação do proprietário do banco; o banco do projeto é remoto e compartilhado. Não acessei esse banco nem alterei credenciais. Para fechar R7, ainda é necessário ambiente de homologação isolado com backup sintético, procedimento do DBA, janela e supervisor de processo aprovados, participação de dois operadores e supervisor, e metas RTO/RPO aceitas pelo responsável. A homologação manual de acessibilidade de R6 também continua gate para R8.

**Saldo:** 2 etapas de execução (R7 em andamento e R8 pendente). O piloto permanece NO-GO.
