# Validação — UI-7.1: CRUD de rotas e corredor

**Executada em:** 24/11/2026 23:49 (`America/Sao_Paulo`)
**Etapa:** 53 de 74
**Checkpoint anterior:** `46fead9`
**Commit:** `7e9b2e8`

## Resultado obtido

Rotas operacionais comuns a Tracker/Dirija Bem possuem `LineString` canônica,
corredor, comprimento, hash e versões imutáveis. API lista, cria, consulta,
versiona e arquiva, com concorrência otimista e auditoria.

## Evidências

- Migration 054 aplicada/idempotente.
- Prova MariaDB bloqueou alteração da versão e fez rollback sem resíduos.
- Validações cobrem coordenadas, ponto repetido, corredor e hash determinístico.
- **7 testes focados** e **493 backend** passaram; 12 opt-in pulados.

## Limitações

Desenho visual, pontos obrigatórios e paradas previstas serão adicionados junto
da execução/detecção, sem alterar versões já persistidas.

## Conclusão

**Aprovada.** A rota planejada agora é um objeto operacional versionado.
