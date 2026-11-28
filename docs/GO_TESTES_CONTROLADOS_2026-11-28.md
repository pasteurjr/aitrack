# Decisão para testes controlados — 28/11/2026

## Decisão

**GO para continuar testes controlados com dados sintéticos, simuladores e serviços locais.**

**NO-GO para monitorar clientes/veículos reais ou enviar mensagens, chamadas e comandos.** Essa é uma decisão separada para operação real, não um impedimento aos testes atuais.

Nenhuma senha foi alterada. Por determinação do proprietário, credenciais ficam fora do escopo desta rodada de testes e serão tratadas antes de eventual implantação real.

## Revisão dos sete itens

| Item | Resultado do teste | O que falta |
|---|---|---|
| 1. Continuidade operacional R7 | Backup/restauração, reinício, rollback e reconciliação passaram em duas MariaDB descartáveis. API loopback recuperou readiness; 0 perda/duplicação. | Exercício acompanhado por 2 operadores e supervisor fica para validar usabilidade do procedimento. |
| 2. Detecção | O ensaio sintético atual documenta FNR de 70% quando o score é usado sozinho. | Acrescentar casos sintéticos e avaliar detectores independentes sem declarar dados sintéticos como desempenho real. Score isolado continua fora do fluxo autônomo. |
| 3. IA e ações | 49 testes de provedor, fallback, autonomia, mensagem e voz passaram usando clientes falsos e servidor local. | Integração de fornecedor sandbox fica para quando houver credenciais e ambiente de teste do fornecedor. Nenhuma chamada real foi feita. |
| 4. Acessibilidade | App 1: 1 teste passou. App 2: 98 testes passaram. Builds TypeScript/Vite passaram. | Leitor de tela e validação por operador continuam para homologação da interface, sem impedir a suíte automatizada. |
| 5. Segurança técnica local | `npm audit` reportou zero vulnerabilidades conhecidas nos dois frontends. `pip-audit` reportou zero vulnerabilidades conhecidas nas dependências listadas em `requirements-monitors.txt`. | DAST/TLS pertencem ao ambiente publicado e não são pré-requisito para o ensaio local em loopback. |
| 6. Credenciais | Nenhuma senha foi modificada ou usada em novas conexões. | Tratamento deliberadamente adiado até a preparação de implantação real, conforme instrução do proprietário. |
| 7. Organização do piloto | Existe roteiro R7 com cenários sintéticos, critérios de parada, registro e proposta de RTO/RPO. | Para testes, usar frota sintética, sandbox local e sem destinatários reais. Aprovação do piloto com dados reais só será discutida na etapa de implantação. |

## Validações executadas nesta rodada

- `npm audit --json` — zero vulnerabilidades nos dois frontends.
- `pip-audit -r requirements-monitors.txt -f json` — zero vulnerabilidades conhecidas no conjunto auditado.
- App 1 — 1 teste, build TypeScript/Vite aprovado.
- App 2 — 98 testes em 22 arquivos, build TypeScript/Vite aprovado. Bundle de 574 kB gera aviso de tamanho.
- Backend focado — 49 testes de IA, fallback, autonomia, sandbox de mensagem/voz e playbooks passaram.
- R7 MariaDB isolado — dump, restore, restart, rollback do código e reconciliação passaram. Evidência `docs/evidence/UI_R7_MARIADB_RECOVERY_2026-11-28.json`.

## Próximo trabalho de teste

Continuar o ensaio ponta a ponta com os simuladores Tracker e Dirija Bem, observar os eventos e incidentes, confirmar comportamento dos agentes em modo simulado e registrar falhas. Manter somente dados sintéticos e recibos locais. Isso é permitido sob a decisão GO para testes controlados.
