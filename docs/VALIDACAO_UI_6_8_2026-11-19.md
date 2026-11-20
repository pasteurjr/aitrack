# Validação — UI-6.8: aprovação humana

**Executada em:** 19/11/2026 23:16 (`America/Sao_Paulo`)
**Etapa:** 46 de 74
**Checkpoint anterior:** `6194ff1`
**Commit de implementação:** `bfc51e6`

## Resultado esperado

Reter ação acima da autonomia até aprovação explícita, versionada e com prazo.

## Resultado obtido

Solicitação persiste versão da ação, papel, motivo, snapshot de política e
expiração. Decisão exige ator diferente do solicitante, papel suficiente,
versão e idempotência. Aprovação libera; rejeição ou expiração cancelam.

## Evidências

- Migration 049 aplicada/idempotente.
- Prova MariaDB aprovou com humano distinto, bloqueou alteração da decisão
  terminal e fez rollback sem resíduos.
- Testes cobriram autoaprovação, papel insuficiente, expiração, rejeição e
  bloqueio de claim antes da aprovação.
- **6 testes focados** e **456 backend** passaram; 12 opt-in pulados.

## Limitações

- A autenticação/RBAC transversal ainda é futura; o serviço falha fechado e
  recebe identidade tipada de camada confiável, não do corpo livre da ação.

## Conclusão

**Aprovada.** A autonomia do agente possui barreira humana auditável e segura.
