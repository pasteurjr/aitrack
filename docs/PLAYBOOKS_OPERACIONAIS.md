# Playbooks operacionais de monitoramento veicular

**Versão:** 1.0 · **Ambiente de exercício:** isolado, dados sintéticos

## Regras comuns

1. Confirme o identificador do veículo e a fonte: Tracker, Dirija Bem ou dados fundidos.
2. Verifique o horário da última posição e a saúde da integração antes de classificar.
3. Registre evidência, decisão, responsável e correlação no incidente.
4. A IA pode resumir e recomendar. O operador mantém controle e usa takeover quando necessário.
5. Em exercício, mensagens, voz e comandos são sandbox; nenhuma pessoa real é contatada.
6. Se houver dúvida sobre risco imediato, escale ao supervisor pelo procedimento aprovado.

## PL-01 — incidente crítico novo

**Gatilho:** incidente crítico criado por regra ou agente.

**Ações:** validar placa e fonte; abrir timeline; reconhecer; assumir atendimento; comparar
posição, eventos e evidências; registrar tentativa de contato apenas no sandbox; escalar se
SLA vencer; resolver somente com código e justificativa.

**Aceite:** estado percorre `new → triage → in_progress → resolved`; autoria e timeline
permanecem legíveis; nenhum contato externo real no exercício.

## PL-02 — classificar falso positivo

**Gatilho:** operador confirma ruído de GPS, evento duplicado, identidade errada ou regra
incorreta.

**Ações:** conferir telemetria no período, identidade e cerca/limiar; selecionar motivo
específico; registrar observação curta; classificar como falso positivo; preservar o alerta
original e a evidência.

**Aceite:** `detection_outcome=false_positive`, motivo permitido e registro auditável. Não
apagar incidente para “limpar” a fila.

## PL-03 — falso negativo reportado

**Gatilho:** operador identifica ocorrência que não gerou incidente.

**Ações:** criar relato com veículo, período, tipo, severidade, evidência e motivo
(`detector_gap`, `telemetry_gap`, `delayed_data`, entre outros); atribuir revisão ao time
de monitoramento; não alterar score ou regra automaticamente.

**Aceite:** incidente de falso negativo fica identificável e alimenta avaliação do detector.

## PL-04 — saída de cerca

**Gatilho:** veículo atribuído a área permitida aparece fora da geometria.

**Ações:** confirmar cerca ativa e janela local; validar posição, precisão e histerese;
comparar fontes se houver; aguardar confirmação do detector; reconhecer ou classificar
ruído com justificativa.

**Aceite:** evento contém entrada/saída, geometria e posição temporalmente coerentes.

## PL-05 — veículo offline ou Tracker indisponível

**Gatilho:** atraso de posição ou integração Tracker degradada/outage.

**Ações:** consultar última posição, ignição, viagem, manutenção e saúde da integração;
se a fonte inteira caiu, abrir incidente técnico de integração em vez de atribuir falha
individual ao veículo; informar operador e acompanhar recuperação.

**Aceite:** estado técnico separado do incidente veicular; retomada não duplica ocorrência.

## PL-06 — Dirija Bem indisponível

**Gatilho:** falha ou atraso de importação de viagem/evento comportamental.

**Ações:** verificar heartbeat e offset; manter eventos previamente persistidos; marcar
visão comportamental como desatualizada; não inventar telemetria nem alterar banco de origem;
reconciliar após recuperação.

**Aceite:** atraso visível, dados originais preservados e replay idempotente.

## PL-07 — IA fora ou timeout

**Gatilho:** timeout, circuit breaker aberto ou resposta inválida.

**Ações:** registrar código sanitizado; usar fallback de regra; exigir revisão humana; manter
ações externas pendentes de autorização; acompanhar probe de recuperação.

**Aceite:** agente não afirma decisão que não obteve; nenhuma mensagem/voz/comando não
autorizado sai; circuito recupera após probe válido.

## PL-08 — mensagem/voz sem resposta

**Gatilho:** sandbox ou provedor indica falha, timeout, opt-out ou número inválido.

**Ações:** consultar tentativas e política de contato; respeitar janela/cooldown/opt-out;
usar dead-letter para revisão após limite; não repetir indefinidamente.

**Aceite:** uma ação lógica, retries limitados, destinatário não contatado fora da política.

## PL-09 — takeover humano

**Gatilho:** operador decide assumir de um agente autônomo.

**Ações:** assumir com versão atual; registrar motivo; confirmar que novas decisões do agente
ficam suspensas; continuar atendimento manual; devolver controle somente após registro.

**Aceite:** a versão concorrente antiga recebe 409/conflito ou é ignorada; sem execução
autônoma durante takeover.

## PL-10 — dois operadores no mesmo incidente

**Gatilho:** duas pessoas tentam alterar o mesmo incidente.

**Ações:** cada operador lê versão; primeira alteração é gravada; segunda recebe conflito,
recarrega timeline e reaplica apenas se ainda fizer sentido.

**Aceite:** atualização otimista impede sobrescrita silenciosa; autor e motivo preservados.

## PL-11 — comando crítico

**Gatilho:** bloqueio, buzina ou outro comando de dispositivo habilitado no futuro.

**Ações:** conferir suporte do protocolo, veículo, risco, justificativa e estado seguro;
solicitar aprovação de supervisor distinto; testar somente em simulador/dispositivo
autorizado e plano de reversão.

**Aceite:** solicitante não aprova a própria ação; auditoria completa; nenhum comando em
veículo real durante treinamento.

## PL-12 — reinício e reconciliação

**Gatilho:** aplicação ou worker reinicia.

**Ações:** confirmar readiness; consultar leases vencidos, filas e dead-letter; verificar
última correlação persistida; reprocessar idempotentemente; comparar totais recebidos,
persistidos, rejeitados e pendentes.

**Aceite:** zero perda não explicada, duplicidade zero e backlog drenando.

## Registro de exercício

Para cada execução, registrar: playbook, versão do sistema, ambiente, facilitador,
participantes, horário início/fim, IDs sintéticos, resultado esperado/obtido, desvios,
capturas, ações corretivas e aprovação do responsável operacional.
