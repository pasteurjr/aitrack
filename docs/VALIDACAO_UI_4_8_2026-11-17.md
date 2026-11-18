# Validação — UI-4.8: alimentação removida e baixa tensão externa

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 19 de 74  
**Checkpoint anterior:** `13030f6`

## Resultado esperado

Protocolos com sinal comprovado devem gerar episódios de alimentação removida e
baixa tensão com amostras consecutivas, histerese e cooldown, reduzindo falsos
positivos sem esconder falsos negativos.

## Resultado obtido

- O detector consome somente `external_voltage` persistido e confirmado no catálogo;
  não declara bateria interna do rastreador.
- Duas políticas versionadas foram criadas em `draft`, escopo `source:tracker`:
  alimentação removida (≤2,0 V, recuperação ≥8,0 V, 2+2 amostras, cooldown 15 min)
  e baixa tensão externa (>2,0 e ≤11,6 V, recuperação ≥12,2 V, 3+3 amostras,
  cooldown 30 min).
- Política em rascunho não executa. O motor também exige veículo `armed`; veículo
  desarmado não consulta política nem cria episódio.
- Estado por política/sensor mantém contadores, episódio ativo, última evidência e
  cooldown. Episódios preservam tipo, severidade, valores de disparo/recuperação,
  mínimo, quantidade de evidências, política, veículo, sensor e correlação única.
- Um savepoint isola falha do detector: a leitura do sensor permanece persistida e
  qualquer alteração parcial do detector é revertida.
- API/UI exibem episódios abertos/resolvidos e políticas disponíveis; ativação
  continua exigindo operador/motivo e não envia comando físico.

## Evidências

- Migration `028_create_power_detector.sql` aplicada e dry-run posterior:
  **0 migrations pendentes**.
- Prova transacional MariaDB ativou temporariamente as duas políticas, armou o
  veículo 1 e processou 12 leituras. Um pulso isolado de 0,5 V não abriu episódio;
  duas baixas abriram `power_removed`, duas recuperações resolveram; três leituras
  baixas abriram `low_external_voltage` e três recuperações resolveram.
- Episódios comprovados antes do rollback: alimentação removida 0,4→8,3 V e baixa
  tensão 11,0→12,5 V, ambos resolvidos. Rollback deixou **0 episódios**, políticas
  em `draft` e veículo `disarmed`.
- Testes puros cobrem pulso isolado, amostras consecutivas, rebote na recuperação,
  histerese, faixa que separa perda de energia/baixa tensão e rejeição de política
  permissiva demais — cobrindo falsos positivos e falsos negativos esperados.
- API real: contrato `detector-episodes.v1`, zero episódios; duas políticas draft.
- Navegador real 1440×900 mostrou estado desarmado, nenhum episódio, aviso de que
  drafts não executam e dois botões distintos para ativar as políticas Tracker.
- Backend: **282 aprovados e 12 integrações opt-in puladas**.
- Frontend: **79 aprovados** em 16 suítes; TypeScript e build aprovados.

## Limitações e segurança

- Nenhuma política está ativa ao final. Limites devem ser homologados com hardware e
  operação antes da ativação fora do simulador.
- Os limiares são de tensão externa. Estado de bateria interna só poderá existir se
  um protocolo passar a entregar e comprovar esse sinal separadamente.
- Episódios ainda não são incidentes operacionais nem disparam mensagem; correlação
  e automação seguirão os blocos de agentes/ações.
- O detector é síncrono ao recebimento e usa savepoint. Fila/reprocessamento técnico
  para falha persistente pertence ao endurecimento operacional posterior.

## Conclusão

**Aprovada.** O sistema detecta e persiste os dois cenários com proteção explícita
contra ruído, recuperação segura e nenhuma ativação implícita; falso positivo e
falso negativo possuem testes determinísticos.
