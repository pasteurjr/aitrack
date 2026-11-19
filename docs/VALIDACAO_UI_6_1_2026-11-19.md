# Validação — UI-6.1: fila operacional de ações

**Executada em:** 19/11/2026 16:01 (`America/Sao_Paulo`)  
**Etapa:** 39 de 74  
**Checkpoint anterior:** `f53243d`  
**Commit de implementação:** `39000f6`

## Resultado esperado

Persistir ação com tipo, alvo, payload, política, prioridade, estado, tentativas,
correlação e chave idempotente.

## Resultado obtido

- `action_queue` é contrato comum para notificação interna, mensagem, voz,
  autoridades e comando veicular.
- Alvo é referência tipada; payload e snapshot da política são JSON validados.
- Fila guarda prioridade, estado, versão, tentativas, lease, erros, correlação,
  causa e ligação opcional à decisão/run.
- Timeline `action_events` é append-only e idempotente.

## Evidências

- Migration 042 aplicada/idempotente.
- Prova real persistiu notificação `high/pending`, payload/política válidos;
  duplicata foi barrada por unique e update/delete do evento por SQLSTATE 45000.
- Rollback deixou zero resíduo.
- **2 testes focados** e **427 testes backend** aprovados; 12 opt-in pulados.

## Limitações

- Esta etapa define armazenamento; transições e retry entram na UI-6.2.
- Nenhum canal externo foi implementado ou chamado.

## Conclusão

**Aprovada.** Existe um contrato comum, rastreável e fail-closed para as ações.
