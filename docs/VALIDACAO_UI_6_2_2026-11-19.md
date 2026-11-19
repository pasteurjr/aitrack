# Validação — UI-6.2: estados e idempotência das ações

**Executada em:** 19/11/2026 16:04 (`America/Sao_Paulo`)  
**Etapa:** 40 de 74  
**Checkpoint anterior:** `7484600`  
**Commit de implementação:** `40bc9b5`

## Resultado esperado

Transições atômicas, retry sem duplicidade e proteção contra dois operadores
ou workers alterando a mesma ação.

## Resultado obtido

- Máquina cobre aprovação, claim/lease, envio, entrega, resposta, falha, retry,
  dead-letter, cancelamento e simulação.
- Toda mutação exige versão esperada e idempotency key; replay retorna estado
  atual sem repetir evento.
- Claim incrementa tentativa e registra worker/lease; falha/retry limpam lease.
- Identidade, estados finais e exclusão são bloqueados no banco.

## Evidências

- Migration 043 aplicada/idempotente.
- Prova real percorreu `pending → claimed → failed → pending → claimed →
  sent → delivered → responded`, com duas tentativas e oito eventos.
- Replay final foi idempotente; reabertura/exclusão terminal falharam com 45000.
- Rollback confirmou zero resíduo.
- **3 testes focados** e **430 testes backend** aprovados; 12 opt-in pulados.

## Conclusão

**Aprovada.** Retry e concorrência não duplicam o efeito lógico da ação.
