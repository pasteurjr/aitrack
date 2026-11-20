# Validação — UI-6.6: templates versionados

**Executada em:** 19/11/2026 23:11 (`America/Sao_Paulo`)
**Etapa:** 44 de 74
**Checkpoint anterior:** `1d857cf`
**Commit de implementação:** `8892d59`

## Resultado esperado

Usar template aprovado, com variáveis tipadas, idioma, versão e prévia.

## Resultado obtido

Chave estável agrupa versões imutáveis com locale, canal, hash e autoria. Schema
e renderização exigem correspondência exata de tokens, tipos e limites. Uma
única versão fica aprovada; a prévia não enfileira nem envia ação.

## Evidências

- Migration 047 aplicada/idempotente.
- Prova MariaDB aprovou versão, bloqueou alteração do corpo e fez rollback sem
  resíduos.
- Testes rejeitaram variável extra/ausente, tipo incorreto, token divergente e
  caractere de controle.
- **3 testes focados** e **449 backend** passaram; 12 opt-in pulados.

## Limitações

- Interface administrativa de templates não pertence a esta etapa.
- O dispatcher deverá exigir explicitamente versão aprovada ao montar a ação.

## Conclusão

**Aprovada.** Conteúdo enviado pode ser reconstruído por versão/hash e não pode
ser alterado depois da aprovação.
