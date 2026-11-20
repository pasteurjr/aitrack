# Validação — UI-6.4: mensagem em sandbox

**Executada em:** 19/11/2026 23:06 (`America/Sao_Paulo`)
**Etapa:** 42 de 74
**Checkpoint anterior:** `5bbed3e`
**Commit de implementação:** `f3028e0`

## Resultado esperado

Enviar mensagem exclusivamente a destino de teste, com credencial externa ao
código e recibo persistente, sem risco de contato com proprietário real.

## Resultado obtido

- O dispatcher consome somente ação `send_message` em estado `pending` ou
  `approved`, usando lock, versão e eventos da fila.
- HTTP sem TLS só é permitido em loopback; endpoint HTTPS precisa identificar
  sandbox/test e a allowlist aceita apenas referências `TEST-`/`SANDBOX-`.
- Token vem do ambiente; `public_id` estável segue como chave idempotente.
- Recibo guarda hashes de destino/requisição, identificador do provedor e
  resposta sanitizada, sem telefone nem corpo em claro.
- Falha do sandbox registra `failed`; sucesso registra recibo único e `sent`.

## Evidências

- Migration 045 aplicada; segunda execução reportou zero pendências.
- Servidor HTTP local real respondeu 202 e confirmou autorização, marcador
  sandbox e chave idempotente; destino fora da allowlist foi recusado.
- Prova MariaDB transacional confirmou FK, inserção, bloqueio de alteração pelo
  trigger e rollback com zero resíduos.
- **8 testes focados** e **436 testes backend** passaram; 12 integrações opt-in
  foram puladas por desenho da suíte.
- Inspeção do recibo confirmou ausência do destino em claro e do token.

## Limitações e segurança

- Nenhum número, proprietário ou destinatário real foi usado ou acionado.
- O provedor sandbox precisa honrar a chave idempotente para cobrir queda entre
  aceite HTTP e commit local.
- Entrega, leitura e resposta assíncronas são a próxima etapa, UI-6.5.

## Conclusão

**Aprovada.** O canal de mensagem está conectado à fila e falha fechado fora de
ambiente/destino de teste, com recibo durável e auditável.
