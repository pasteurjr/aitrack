# Validação — UI-4.7: estados armado/desarmado

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 18 de 74  
**Checkpoint anterior:** `d66d847`

## Resultado esperado

Manter estado patrimonial armado/desarmado por veículo, com transições autorizadas,
responsável, horário, escopo, concorrência segura e histórico auditável.

## Resultado obtido

- `vehicle_security_state` mantém estado e versão corrente por veículo; migration
  inicializou os 26 veículos como `disarmed`, sem armar monitoramento implicitamente.
- `vehicle_security_history` preserva origem/destino, versões, ator, fundamento da
  autorização, motivo, correlação e horário de cada transição.
- A máquina aceita apenas `armed`/`disarmed`, exige ator humano/sistema completo,
  motivo, fundamento permitido e `expected_version`.
- A versão otimista impede dois operadores de sobrescreverem a mesma decisão; uma
  repetição com a mesma correlação é idempotente e não duplica histórico.
- A API retorna 400 para payload/transição inválida, 404 para veículo ausente e 409
  para conflito de versão/correlação.
- A aba Sensores ganhou controle patrimonial por veículo com estado, versão, última
  autoria, motivo, ID/nome do operador, fundamento, ação e histórico expansível.

## Evidências

- Migration `027_create_security_arming_state.sql` aplicada; nova execução:
  **0 migrations pendentes**. Estado da frota: **26 desarmados, 0 armados** ao final.
- Prova real no veículo operacional 1: `disarmed v1 → armed v2`; repetição retornou
  `idempotent=true` e manteve v2; tentativa com v1 retornou HTTP 409; encerramento
  `armed v2 → disarmed v3` deixou duas entradas de histórico.
- API real final: veículo 1 `disarmed`, versão 3, duas transições, responsável e
  fundamento `operator_protocol` preservados.
- Navegador real 1440×900 mostrou `DESARMADO`, escopo veículo 1, versão 3, botão de
  armar, campos de autorização e `Histórico auditável (2)` com o motivo final.
- Backend: **273 aprovados e 12 integrações opt-in puladas**.
- Frontend: **78 aprovados** em 16 suítes; TypeScript e build aprovados.

## Limitações e segurança

- “Armado” habilita o estado patrimonial lógico; não envia comando físico ao veículo
  e não garante por si só que exista detector ativo. A UI mantém essa separação.
- A API exige autoria/fundamento, mas autenticação central e validação de papéis ainda
  pertencem ao bloco de produção. Até lá, o endpoint mutável deve ficar restrito à
  rede de homologação.
- `scheduled_policy` é aceito apenas para ator `system`; solicitação do proprietário
  e protocolo operacional exigem ator `human`. O agendador ainda não existe.
- O histórico da prova foi deliberadamente preservado: são transições reais de
  homologação no veículo simulado e o estado final seguro é `disarmed`.

## Conclusão

**Aprovada.** O sistema possui estado patrimonial concorrente, idempotente e
auditável, com escopo e responsabilidade explícitos, sem confundi-lo com comando de
hardware.
