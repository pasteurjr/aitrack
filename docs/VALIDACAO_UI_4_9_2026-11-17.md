# Validação — UI-4.9: offline contextualizado

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 20 de 74  
**Checkpoint anterior:** `8aa7893`

## Resultado esperado

Detectar veículo offline sem confundir repouso, manutenção ou pane da integração com
falha individual, considerando frequência esperada, viagem, ignição e saúde da fonte.

## Resultado obtido

- Um worker supervisionado a cada 30 s avalia ausência de dados; detecção não depende
  da chegada de um pacote que, por definição, não existe durante offline.
- O heartbeat da ingestão atualiza `integration_health`. Se toda a fonte Tracker
  estiver sem sucesso além do limite, o veículo é suprimido como
  `integration_outage`, evitando dezenas de falsos incidentes individuais.
- `vehicle_monitoring_context` permite janela de manutenção por veículo com motivo e
  autoria. Veículo desarmado também é suprimido.
- O contexto usa última posição, velocidade e ignição: movimento >5 km/h usa 60 s;
  ignição ligada usa 120 s; repouso/estado desconhecido usa 600 s. A política ainda
  registra intervalo esperado de 5 s e exige duas verificações para abrir/recuperar.
- Estado do detector mantém suspeita, offline, recuperação, contadores, episódio,
  última posição, contexto e motivo de supressão.
- Episódio `offline` usa segundos sem posição como evidência; a UI não os apresenta
  incorretamente como volts.
- A política `vehicle-offline` nasce em `draft`, escopo Tracker, e só aparece como
  opção de ativação na capacidade Posição GPS.

## Evidências

- Migration `029_create_contextual_offline_detector.sql` aplicada e nova execução:
  **0 migrations pendentes**.
- Prova MariaDB transacional no veículo 1 confirmou, em ordem:
  `vehicle_disarmed`, `integration_outage` e `maintenance`, todos sem episódio;
  depois `suspect` aos 70 s e abertura `offline` aos 71 s em contexto `moving`;
  uma leitura fresca iniciou recuperação e a segunda resolveu aos 2 s.
- Episódio antes do rollback: tipo offline, 71 s no disparo, 2 s na recuperação e
  metadata `context=moving/threshold=60`. Rollback deixou **0 episódios**, política
  `draft` e veículo `disarmed`.
- Runtime real após reinício: Tracker `healthy` com heartbeat renovado pelo simulador,
  zero estados offline (política não ativa) e worker supervisionado sem erro.
- Navegador real mostrou `Ativar vehicle-offline v1 (source:tracker)`, estado
  desarmado e aviso de que políticas em rascunho não executam.
- Testes cobrem janelas por contexto, suspeita isolada, abertura, recuperação com
  rebote, supressões e rejeição de política permissiva.
- Backend: **289 aprovados e 12 integrações opt-in puladas**.
- Frontend: **79 aprovados** em 16 suítes; TypeScript e build aprovados.

## Limitações e segurança

- A política está em draft; portanto o worker não cria episódios no ambiente atual.
  Ativação exige homologação e veículo armado.
- Manutenção possui persistência e é considerada pelo motor, mas ainda não ganhou
  formulário próprio na interface.
- Viagem é inferida por velocidade/ignição das leituras disponíveis. Integração com
  agenda formal de viagem poderá refinar o contexto sem reduzir as proteções atuais.
- Episódio ainda não é incidente nem mensagem. O runtime de agentes e as ações serão
  responsáveis por correlação, decisão e comunicação posterior.

## Conclusão

**Aprovada.** Offline deixou de ser um timeout cego: diferencia veículo, fonte,
manutenção e contexto de uso, exige confirmação/recovery e permanece inativo até
autorização explícita.
