# Validação — UI-4.6: ativar política, não hardware

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 17 de 74  
**Checkpoint anterior:** `eb2dafb`

## Resultado esperado

Deixar inequívoco que habilitar monitoramento significa ativar uma política
operacional versionada. Controle físico só pode aparecer quando a capacidade do
protocolo/modelo estiver confirmada e existir contrato seguro de comando.

## Resultado obtido

- Cada sensor mostra o estado da detecção separadamente do ciclo físico do sensor.
- Sem política aplicável, a interface informa `Detecção não configurada` e esclarece
  que o sensor continua transmitindo e nenhum estado físico foi alterado.
- Quando existe versão `draft`, o operador deve informar identidade e motivo antes de
  ativá-la; a chamada inclui correlação por veículo/política e atualiza para
  `Detecção operacional ativa` após confirmação do backend.
- A ativação exibe chave/versão da política e declara que não liga/desliga hardware.
- A API de sensores consulta comandos no perfil ativo mais recente e separa
  `commands` de `confirmed_commands`.
- Como buzzer e imobilização remota estão `unknown` nos protocolos atuais, a tela não
  apresenta botão de bloqueio/acionamento; mostra uma advertência explícita.

## Evidências

- Prova real API/MariaDB criou uma política `draft` de ignição para o veículo 1,
  ativou-a e confirmou `active_key`, auditorias `created`/`activated`, ator e duas
  correlações. A política sintética e sua auditoria foram removidas ao final:
  **0 resíduos**.
- API real de SIM-1000/Suntech: dois comandos catalogados (`buzzer_activation` e
  `remote_immobilization`) com suporte `unknown`; `confirmed_commands=[]`.
- Navegador real 1440×900: cinco cartões exibiram `Detecção não configurada`, aviso
  de que nenhum estado físico foi alterado e nenhum botão de bloqueio/acionamento.
- Backend: **264 aprovados e 12 integrações opt-in puladas**.
- Frontend: **77 aprovados** em 16 suítes; TypeScript e build aprovados.
- Teste de interface prova ativação de draft com operador/motivo, atualização para
  ativo e ausência de comando físico.

## Limitações e segurança

- Não existe política operacional ativa após a validação. Regras reais só devem ser
  criadas com limites homologados nas etapas dos detectores.
- A autoria é obrigatória e auditada, mas autenticação/roles transversais ainda serão
  implementados no bloco de produção; a API mutável permanece restrita ao ambiente
  controlado.
- Esta etapa não implementa envio ao equipamento. Solicitação, ACK/NACK, timeout,
  idempotência e autorização crítica pertencem às UI-4.10/UI-4.11.
- Uma capacidade confirmada futuramente será apenas informada pela tela; ela não vira
  botão executável antes do contrato seguro de comando.

## Conclusão

**Aprovada.** A interface não usa “ativar sensor” como sinônimo enganoso: ativa uma
regra auditável e mantém comandos físicos ocultos enquanto o suporte não é comprovado.
