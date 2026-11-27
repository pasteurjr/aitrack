# R8 — reavaliação de prontidão do piloto

**Data:** 27/11/2026 (`America/Sao_Paulo`)
**Etapa:** 8 de 8 — decisão concluída
**Checkpoint da revisão:** `05db271`
**Decisão:** **NO-GO — manter o piloto bloqueado**

## Resultado esperado

Revisar gates de segurança, detecção, acessibilidade, autonomia e operação, vincular as evidências atuais e autorizar o piloto somente se todos os requisitos obrigatórios tiverem evidência e aceite.

## Revisão dos gates

| Gate | Evidência revisada | Estado |
|---|---|---|
| Dependências críticas/altas | R1 registrou auditoria de dependências sem achados conhecidos nos frontends na data do ensaio. | Revisar novamente no ambiente e lockfiles do deploy antes do piloto |
| Credenciais históricas | O proprietário dispensou rotação apenas para este ambiente de testes. O histórico permanece e não houve rotação. | Aberto para qualquer uso real |
| Segurança no ambiente alvo | R3 local aceito para simulação. DAST autenticado e TLS do ambiente de implantação não foram executados. | Aberto para implantação |
| Detecção | R4 marcou score isolado como inadequado, com FNR sintético de 70%. | Bloqueado para score como gatilho único; falta aprovação operacional de dados representativos |
| Agentes e canais | R5 validou regras e adaptadores com clientes falsos/loopback. Provedor LLM e canais externos reais não foram homologados. | Simulação aprovada; operação real pendente |
| Acessibilidade | R6 automatizada passou em 98 testes, build e Playwright do login. NVDA/VoiceOver e telas autenticadas aguardam operadores. | Gate humano pendente |
| Continuidade operacional | R7 passou backup/restauração, restart, rollback e recuperação em MariaDB local descartável. Dois operadores, supervisor e metas RTO/RPO aprovadas não participaram. | Gate operacional pendente |
| Piloto controlado | Sem grupo/janela aprovados, suporte, métricas de aborto e aceite formal por produto, segurança e operação. | Pendente |

## Resultado obtido

Os ensaios R6 e R7 aumentaram a evidência automatizada local, mas não satisfazem todos os gates de homologação humana e do ambiente alvo. Não há aprovação para expor clientes, veículos ou proprietários a monitoramento e ações autônomas. Mantém-se **NO-GO**.

## Próximos requisitos antes de uma nova decisão

1. Executar R7 com dois operadores e supervisor, aprovar RTO/RPO e anexar a ata e os resultados.
2. Concluir acessibilidade manual dos fluxos autenticados com tecnologia assistiva.
3. Executar DAST/TLS no ambiente de homologação que será usado.
4. Resolver o tratamento de credenciais e histórico antes de qualquer implantação.
5. Aprovar detecção com amostras representativas e medidas de falsos positivos e falsos negativos por fonte e classe.
6. Homologar provedores LLM e canais em sandbox e aprovar limites de ação.
7. Definir grupo, janela, suporte, consentimento, métricas de sucesso/aborto, responsáveis e rollback.

## Contagem

R8 concluiu sua decisão e registrou NO-GO. **R7 continua em andamento**, portanto resta uma etapa de execução de oito. O piloto não está autorizado.
