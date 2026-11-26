# Validação R5 — agentes, autonomia e ações simuladas

**Data:** 26/11/2026 (`America/Sao_Paulo`)

**Checkpoint antes da etapa:** `11bc9ec`

## Objetivo

Verificar a trilha de decisão do agente e garantir que a proposta do modelo não execute por si só uma ação. Incidentes altos/críticos devem continuar sob revisão humana, falhas do provedor devem usar fallback seguro, e mensagens/voz devem ficar confinadas ao sandbox e à allowlist.

## O que o código faz

- Há adaptadores para Anthropic e OpenAI; a configuração indica o provedor e modelo por versão do agente. Os testes usam SDKs falsos/determinísticos. **Nenhuma chamada real a LLM foi feita nesta etapa**, então isso não prova a qualidade de um modelo específico nem qual modelo está configurado nos agentes armazenados no banco.
- O worker coleta contexto por ferramentas permitidas e solicita uma decisão JSON estruturada. A validação rejeita campos inválidos; o fallback do provedor marca evidência insuficiente, exige revisão humana e não pede comando ao veículo.
- A finalização do run calcula autorização e persiste recibos simulados. Ela não chama os provedores de mensagem, voz ou comando físico.
- Mensagem e voz têm provedores próprios de sandbox, allowlist `TEST-/SANDBOX-`, chave de idempotência e recibos sanitizados. A comunicação é distinta da simulação de autorização do agente.

## Correção aplicada nesta etapa

A autorização considerava o risco e a necessidade de revisão declarados pelo LLM. Isso permitia que uma decisão com risco baixo e `human_review=false` passasse se a severidade original do incidente fosse alta/crítica. Agora `finish_run` recupera a severidade persistida na entrada do run e a entrega à política de autonomia; alto/crítico força `approval_required` mesmo quando o modelo subestima o incidente. Entrada persistida inválida falha fechada.

## Resultado e validação

A suíte focada teve **83 testes aprovados** em 11 arquivos. Um guard no processo bloqueou qualquer conexão MySQL e conexões de rede que não fossem loopback. Os testes de sandbox usaram servidor HTTP local `127.0.0.1`; nenhuma chamada saiu da máquina e nenhum destinatário real foi usado.

O teste novo de integração simulada finaliza um run cujo incidente persistido é crítico, enquanto o modelo propõe risco baixo, revisão falsa e contato com o dono. A autorização gravada exige aprovação, informa a severidade confiável e não grava recibo de ação simulada elegível. Nenhum dispatcher de contato é chamado.

## Limites

Esta etapa prova as barreiras do fluxo local, não a resposta real da Anthropic/OpenAI, nem a entrega de mensagem/ligação por um sandbox de fornecedor. Não houve acesso ao banco real, troca de credencial, chamada externa ou comando de veículo. A homologação real de LLM e canais permanece necessária antes de efeitos reais. O piloto segue NO-GO.

**Evidências:** `docs/evidence/UI_R5_AGENT_SIMULATION_2026-11-26.json`.  
**Testes:** `tests/test_agent_runs.py`, `test_agent_autonomy.py`, `test_agent_analysis_worker.py`, `test_agent_simulation.py`, `test_agent_decision_schema.py`, `test_ai_provider.py`, `test_ai_resilience.py`, `test_message_sandbox.py`, `test_voice_sandbox.py`, `test_communication_outcomes.py`, `test_action_contact_policy.py`.
