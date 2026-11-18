# Validação — UI-5.4: provedores de IA por interface

**Executada em:** 18/11/2026 03:30 (`America/Sao_Paulo`)  
**Etapa:** 27 de 74  
**Checkpoint anterior:** `e9f355c`  
**Commit de implementação:** `aa8c80d`

## Resultado esperado

Permitir troca de provedor/modelo por configuração sem acoplar regras de
monitoramento ao SDK externo.

## Resultado obtido

- `DecisionProvider` define uma única operação neutra: gerar decisão a partir de
  instruções, entrada, contexto, modelo e limites.
- O resultado normalizado contém provedor/modelo, ID externo, decisão v1 validada,
  JSON canônico, SHA-256 e uso de tokens.
- Adaptador Anthropic usa Messages API; adaptador OpenAI usa Responses API com
  armazenamento remoto desabilitado (`store=False`).
- O modelo nunca é hardcoded: vem da versão ativa de configuração. Timeout,
  temperatura e máximo de saída vêm dos limites da requisição.
- O prompt inclui o JSON Schema e proíbe declarar ação como executada; somente
  `proposed_actions` é aceito pelo validador.
- Chaves vêm exclusivamente de `ANTHROPIC_API_KEY` ou `OPENAI_API_KEY` e nunca são
  incluídas em payload, log, banco ou repositório.
- Factory falha explicitamente para provedor desconhecido ou segredo ausente. Não
  troca silenciosamente de modelo/provedor.
- Um adaptador determinístico existe apenas para testes e não é selecionável pela
  factory de produção.

## Evidências

- Ambiente local confirmado: Anthropic SDK `0.57.1` e OpenAI SDK `1.95.1`.
- Clientes falsos comprovaram chamada Anthropic com modelo/timeout configurados,
  ID `msg-1` e uso 123/45 tokens.
- Cliente falso OpenAI comprovou Responses API, modelo configurado, timeout,
  `store=False`, ID `resp-1` e uso 50/20 tokens.
- JSON inválido e objeto fora do contrato v1 geraram erro normalizado, sem decisão.
- Factory sem segredo e provedor desconhecido foram negados.
- **21 testes combinados** e **373 testes backend** aprovados; 12 integrações opt-in
  puladas.
- `ANTHROPIC_API_KEY` e `OPENAI_API_KEY` estavam ausentes; nenhuma chamada de rede
  ou cobrança foi realizada.

## Limitações e segurança

- Nenhum provedor/modelo está ativo no sistema e nenhuma credencial foi cadastrada.
- Custo retorna `null`: estimá-lo sem tabela de preços versionada produziria dado
  falso. O ledger aceita custo medido quando o runtime tiver fonte homologada.
- Timeout do SDK foi configurado, mas fallback e circuit breaker pertencem à UI-5.5.
- O repositório ainda não possui manifesto Python consolidado; a declaração formal
  das versões dos SDKs deve entrar no endurecimento de implantação.

## Conclusão

**Aprovada.** O domínio de monitoramento não depende de Claude, GPT ou outro SDK;
provedor e modelo são intercambiáveis por configuração e toda saída atravessa o
mesmo contrato seguro.
