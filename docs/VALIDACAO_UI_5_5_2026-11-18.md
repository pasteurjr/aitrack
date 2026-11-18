# Validação — UI-5.5: timeout, fallback e circuit breaker

**Executada em:** 18/11/2026 03:34 (`America/Sao_Paulo`)  
**Etapa:** 28 de 74  
**Checkpoint anterior:** `30209f2`  
**Commit de implementação:** `daaa872`

## Resultado esperado

Falha ou latência da IA não pode parar o monitoramento; fallback deve ser explícito,
medido e testado, sem inventar normalidade ou executar ação.

## Resultado obtido

- `ResilientDecisionProvider` envolve qualquer adaptador sem alterar o contrato do
  domínio.
- Circuit breaker thread-safe possui estados fechado, aberto e meio-aberto, limite
  configurável, janela de recuperação e uma única sonda de retomada.
- Falhas consecutivas abrem o circuito; chamadas durante a abertura não chegam ao
  SDK externo.
- Timeout é enviado ao SDK. Mesmo se um cliente devolver resposta depois do prazo,
  a camada descarta esse resultado e o contabiliza como timeout.
- Fallback seguro produz decisão v1 com `insufficient_evidence`, confiança zero,
  risco médio conservador, notificação ao operador e revisão humana obrigatória.
- O fallback não propõe comando veicular, autoridade ou contato automático e fica
  marcado com motivo e provedor primário.
- Snapshot expõe contadores de chamadas, sucessos, falhas, timeouts, rejeições do
  circuito e fallback, além do estado corrente.
- Se fallback não for configurado, a exceção normalizada continua explícita.

## Evidências

- Duas falhas abriram o circuito; a terceira chamada usou fallback sem incrementar
  chamadas do provedor primário.
- Após avançar o relógio além da janela, uma sonda válida fechou o circuito e zerou
  falhas consecutivas.
- Resultado entregue após o timeout foi descartado e virou
  `AI_PROVIDER_TIMEOUT`; `TimeoutError` nativo recebeu a mesma normalização.
- Fallback foi validado pelo schema v1: confiança 0, evidência sistêmica,
  `human_review.required=true` e somente `notify_operator`.
- Sem fallback, primeira falha foi exposta e chamada seguinte retornou
  `AI_CIRCUIT_OPEN`.
- **16 testes focados** e **380 testes backend** aprovados; 12 integrações opt-in
  puladas.

## Limitações e segurança

- Interrupção física de uma conexão depende do timeout implementado pelos SDKs; a
  camada garante que resposta tardia não seja aceita como decisão.
- Métricas ainda residem na instância do processo; persistência/exportação entra na
  etapa de observabilidade.
- O worker de incidentes ainda não foi criado, portanto essa camada não executa no
  fluxo operacional atual.
- Fallback não substitui regra determinística de detecção nem operador humano.

## Conclusão

**Aprovada.** A indisponibilidade de IA deixa de ser uma pane silenciosa: é contida,
medida e convertida em revisão humana segura, sem ação externa automática.
