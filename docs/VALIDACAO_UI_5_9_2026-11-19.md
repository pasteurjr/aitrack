# Validação — UI-5.9: worker de análise de incidente

**Executada em:** 19/11/2026 15:34 (`America/Sao_Paulo`)  
**Etapa:** 32 de 74  
**Checkpoint anterior:** `4440e0a`  
**Commit de implementação:** `95cf492`

## Resultado esperado

Processar incidentes por fila e prioridade, coletar apenas contexto permitido,
chamar o provedor configurado e persistir a decisão de forma idempotente.

## Resultado obtido

- Fila durável guarda agente, incidente, prioridade, estado, tentativas, lease,
  correlação e chave idempotente.
- Severidade define prioridade (`critical` 100, `high` 80, `medium` 50, `low` 20).
- Claim é serializado por lock consultivo curto, compatível com MariaDB 10.3;
  o processamento ocorre fora do lock e pode ser paralelo.
- Lease vencido volta à fila ou vai para `dead` ao esgotar tentativas.
- Worker carrega configuração ativa, usa somente tools permitidas com as fontes
  e limites daquela permissão, cria um run por tentativa e chama o provedor
  resiliente.
- Sucesso conclui decisão/ledger/job; falha finaliza o run explicitamente e
  reagenda ou envia para `dead`, sem fabricar resposta.

## Evidências

- Migration 038 aplicada e repetida com **0 pendências**.
- Prova real criou jobs baixo/crítico; replay da mesma chave retornou o mesmo ID.
- O job crítico foi reclamado primeiro, falhou para `pending` na tentativa 1 e
  chegou a `dead` na tentativa 2.
- A primeira prova revelou `SKIP LOCKED` incompatível com MariaDB 10.3; a solução
  foi corrigida e a prova integral passou depois da troca.
- Limpeza removeu os dois jobs de prova e confirmou **zero resíduo**.
- **4 testes focados** e **411 testes backend** aprovados; 12 opt-in pulados.

## Limitações

- Nenhuma configuração de agente está ativa e não há chaves externas;
  portanto a prova do provedor usou dependência determinística, sem rede/custo.
- Supervisão contínua do worker e observabilidade entram nas etapas de produção.

## Conclusão

**Aprovada.** A análise possui fila idempotente, prioridade, lease, retry e
dead-letter, respeitando configuração, tools e ledger versionados.
