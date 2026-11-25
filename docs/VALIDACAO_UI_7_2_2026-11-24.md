# Validação — UI-7.2: atribuição e execução de rota

**Executada em:** 24/11/2026 23:51 (`America/Sao_Paulo`)
**Etapa:** 54 de 74
**Checkpoint:** `11c0cc4` · **Implementação:** `ad01ecd`

## Resultado obtido

Atribuição referencia uma versão congelada da rota e exatamente um veículo ou
motorista. Fuso IANA, vigência e sobreposição são validados. Execuções possuem
janela, idempotência, versão e estados explícitos com timeline append-only.

## Evidências

- Migration 055 aplicada/idempotente.
- Overnight e transição de DST preservaram os instantes UTC corretos.
- Prova MariaDB bloqueou exclusão da timeline e fez rollback sem resíduos.
- **10 focados** e **496 backend** passaram; 12 opt-in pulados.

## Limitações

Recorrência semanal e painel visual de atribuições permanecem posteriores.

## Conclusão

**Aprovada.** Uma viagem planejada tem alvo, versão e janela inequívocos.
