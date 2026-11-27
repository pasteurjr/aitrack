# R7 — preflight técnico local de operação e recuperação

**Atualizado:** 27/11/2026 (`America/Sao_Paulo`)
**Etapa:** 7 de 8 — em andamento
**Checkpoint pré-etapa:** `295800f`
**Ambiente:** harness determinístico local; SQLite temporário; nenhum serviço externo ou banco compartilhado acessado.

## Objetivo esperado

Preparar e exercitar playbooks, restart, rollback, backup/restauração e reconciliação em homologação, com dois operadores e um supervisor; medir RTO/RPO contra metas aprovadas; provar ausência de perda e duplicação.

## Resultado inicial do preflight — 26/11

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

## Ensaio de recuperação MariaDB isolado — 27/11

O script `aitrackdatadrivr/scripts/run_local_recovery_drill.py` foi concluído contra duas instâncias MariaDB descartáveis, sem rede TCP para o banco. Criou um backup lógico de 91.481 bytes, restaurou em uma segunda instância e iniciou a API exclusivamente em loopback. A versão atual `7ba8479` passou health live/ready antes e depois do reinício e da restauração. O rollback à revisão `11bc9ec` também passou health live/ready, e a versão atual voltou a passar na verificação após o rollback.

As linhas e triggers restauradas foram comparadas com o snapshot. Dois incidentes sintéticos representaram fontes Tracker e Dirija Bem. O replay idempotente preservou três ações e cinco eventos originais. A recuperação de leases moveu uma ação para retry e outra para dead-letter, processou ambas uma vez e a repetição processou zero. Não houve mensagem, chamada, comando, conexão ao banco compartilhado nem acesso externo. Tempos locais observados: 0,713 s para readiness após restart, 1,543 s após restore e 0,845 s para readiness após rollback do código.

Evidência completa: `docs/evidence/UI_R7_MARIADB_RECOVERY_2026-11-27.json`. Validação do script: `python3 -m py_compile scripts/run_local_recovery_drill.py`; execução end-to-end acima. Os testes focados do preflight anterior seguem 5/5 aprovados.

## Decisão e pendências para concluir R7

R7 tem evidência técnica automatizada de restart, backup, restore, rollback de aplicação e reconciliação em MariaDB sintético. O ensaio local não representa janela de serviço, hardware, carga ou topologia de homologação. Para fechar R7 ainda falta o exercício de dois operadores e supervisor e a aprovação formal das metas RTO/RPO pelo responsável operacional. A homologação manual de acessibilidade de R6 também continua gate para R8.

**Saldo:** 2 etapas de execução (R7 em andamento e R8 pendente). O piloto permanece NO-GO.
