# Decisão de prontidão — piloto controlado

**Etapa:** 74/74 — UI-8.12  
**Data:** 25/11/2026 16:46 (`America/Sao_Paulo`)  
**Checkpoint pré-etapa:** `268ada8`  
**Decisão:** **NO-GO — não liberar o piloto neste momento**

## Resultado esperado

A etapa deve decidir, com evidências, se há condições de liberar um grupo piloto com
monitoramento, consentimento, suporte, rollback, critérios de sucesso e aprovação formal.

## Resultado obtido

A decisão é **NO-GO**. A rodada de 74 etapas está encerrada como avaliação e preparação,
mas isso não significa que o piloto esteja autorizado. Os bloqueios abaixo precisam ser
resolvidos e reavaliados antes de qualquer operação real com autonomia ou comunicação a
proprietários.

| Gate de liberação | Evidência atual | Estado |
|---|---|---|
| Dependências sem vulnerabilidades críticas/altas abertas | Auditoria encontrou 16 vulnerabilidades altas transitivas na cadeia `react-scripts`. | **Bloqueado** |
| Credenciais históricas rotacionadas | O working tree foi limpo, mas há ocorrências em commits históricos; rotação efetiva não foi comprovada. | **Bloqueado** |
| Segurança validada no ambiente-alvo | DAST autenticado e validação TLS ainda não executados. | **Bloqueado** |
| Acessibilidade dos fluxos críticos homologada | Testes automatizados passaram; leitor de tela e contraste visual completo não foram homologados. | **Pendente** |
| Procedimentos operacionais exercitados | Playbooks passaram em harness determinístico; exercício com dois operadores e supervisor não ocorreu. Backup, restore, rollback e TLS também carecem de execução em homologação. | **Pendente** |
| Detecção aprovada para uso operacional | Dataset sintético mostrou FNR de 70% usando score `< 70` sozinho. O score não deve ser gatilho único; detector/eventos independentes continuam necessários. | **Bloqueado para score isolado** |
| Canais e autonomia de agentes validados em sandbox | O ensaio técnico não enviou mensagens, não realizou chamadas e não executou comandos físicos. | **Pendente** |
| Suporte, consentimento, métricas, rollback e aprovação formal | O runbook descreve procedimentos, mas exercício/aceite formal do grupo piloto não foi registrado. | **Pendente** |

## Condições para reavaliar

1. Corrigir ou mitigar as 16 vulnerabilidades altas com atualização suportada e build/regressão aprovados.
2. Rotacionar credenciais expostas em histórico e guardar evidência segura da rotação; não inserir segredos no repositório.
3. Executar DAST autenticado e validar TLS no ambiente de homologação, corrigindo achados críticos/altos.
4. Homologar os fluxos de cerca, incidentes e saúde com leitor de tela e revisão visual de contraste.
5. Executar o exercício do runbook com dois operadores e um supervisor; provar backup/restauração, rollback, reinício e reconciliação em homologação.
6. Validar mensagens/voz com provedores sandbox, consentimento e limites de autonomia; manter aprovação humana para ações externas até o aceite.
7. Recalibrar a política de detecção com amostras rotuladas representativas dos dois operadores de dados, publicar falsos positivos/negativos por classe e aprovar limites. Score não pode ser o único detector enquanto o FNR for inaceitável.
8. Registrar responsável, grupo, janela, métricas de sucesso/aborto, canal de suporte, plano de rollback e aprovação formal antes do piloto.

## Evidências consultadas

- `docs/VALIDACAO_UI_8_8_2026-11-25.md` — segurança e privacidade;
- `docs/VALIDACAO_UI_8_9_2026-11-25.md` — acessibilidade;
- `docs/VALIDACAO_UI_8_10_2026-11-25.md` — playbooks operacionais;
- `docs/VALIDACAO_UI_8_11_2026-11-25.md` — runbook e contingência;
- `docs/VALIDACAO_UI_7_10_2026-11-25.md` — qualidade do score;
- `docs/SEGURANCA_PRIVACIDADE_OPERACIONAL.md` — política operacional.

## Validação desta decisão

O resultado NO-GO foi conferido contra as evidências listadas: nenhum gate pendente foi
marcado como aprovado e nenhum teste sintético foi tratado como homologação de produção.
Não houve deploy, contato com clientes, envio externo ou alteração de bancos nesta etapa.

A etapa 74/74 conclui a rodada de planejamento e avaliação. A liberação real permanece
condicionada à conclusão comprovada dos gates acima e a uma nova decisão formal.
