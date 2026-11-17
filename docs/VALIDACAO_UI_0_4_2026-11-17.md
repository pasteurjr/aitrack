# Validação — UI-0.4: estados comuns de dados assíncronos

**Executada em:** 17/11/2026 11:08 (`America/Sao_Paulo`)  
**Etapa:** 7 de 74  
**Implementação original:** `b6076aa`

## Resultado esperado

Telas que dependem de API devem reutilizar um contrato visual e acessível para carregamento, vazio, erro e dado desatualizado, com testes dos quatro estados.

## Resultado obtido

`AsyncDataState` centraliza as variantes `loading`, `empty`, `error` e `stale`, atribui papéis acessíveis (`status` ou `alert`) e oferece ações opcionais de nova tentativa e retorno. O componente está aplicado a dashboard, timeline, análises, monitores, detalhe do monitor, catálogo, incidentes e partes da frota unificada. Nenhum dado padrão é criado quando uma consulta falha.

## Evidências

- Busca estática encontrou uso compartilhado nas telas operacionais citadas.
- Testes específicos: **12 aprovados** (`AsyncDataState`, `MonitorDashboard`, `EventsTimeline`).
- TypeScript: `npx tsc --noEmit` aprovado.
- Regressão da etapa anterior: suíte completa com **65 testes frontend** e build aprovados no mesmo ciclo de trabalho.

## Limitações

- O componente é comum, mas estilos ainda são inline; unificação de tema não faz parte desta etapa.
- Avisos de dados de compatibilidade de navegadores desatualizados permanecem sem impacto no resultado.

## Conclusão

**Aprovada.** A pendência era de reconciliação do plano com código já incorporado à `main`.
