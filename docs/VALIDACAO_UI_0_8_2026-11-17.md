# Validação — UI-0.8: Tracker e Dirija Bem na visão unificada

**Executada em:** 17/11/2026 11:27 (`America/Sao_Paulo`)  
**Etapa:** 11 de 74  
**Implementação base:** `ae6037f`

## Resultado esperado

Origem inequívoca em lista, detalhe, eventos e superfícies operacionais, preservando visão conjunta, filtros e totais corretos.

## Resultado obtido

- A frota unificada mantém itens `tracker`, `dirijabem` e `both`, com badge, identidade, modo e última comunicação.
- Filtros por fonte contam um item `both` em ambas as fontes sem duplicá-lo no total geral.
- Seleção Tracker, Dirija Bem ou vinculada controla corretamente as duas seleções da aplicação.
- `VehicleDetailHeader` mostra cada proveniência separadamente.
- Incidentes já exibem `Tracker`, `Dirija Bem` ou `Tracker + Dirija Bem` conforme `primary_source`.
- Eventos comportamentais passaram a carregar `source` explicitamente no runtime e no histórico persistido; a timeline ganhou filtro de origem e badge, e o detalhe do monitor mostra a fonte.
- A interface não infere origem pelo texto do `device_id`.

## Evidências

- API real `/api/v1/vehicles`: **26** identidades; 9 `tracker_only`, 16 `app_only` e 1 `both`; zero identidades sem telemetria.
- Teste de frota cobre totais: geral 3, Tracker 2, Dirija Bem 2 com um item `both`.
- Teste da timeline comprova isolamento pelo filtro Dirija Bem.
- Teste backend comprova `source=tracker` no evento de runtime e no contrato `/api/events`, incluindo fallback explícito para registros históricos.
- Suíte backend: **244 aprovados, 12 pulados** após o teste adicional.
- Suíte frontend: **73 aprovados**.
- TypeScript e build: aprovados.

## Limitações

- O motor comportamental atual recebe eventos Tracker; a futura ingestão comportamental Dirija Bem deverá informar `source=dirijabem` sem depender do identificador `APP-*`.
- Ainda não existe tela de relatórios. Relatórios separados/unificados e rastreáveis pertencem à etapa 59/74; esta etapa não cria relatório fictício.
- O backend já em execução precisa ser reiniciado de forma controlada para expor o novo campo em runtime; os contratos foram validados por teste sem interromper o processo de outra sessão.

## Conclusão

**Aprovada.** As superfícies existentes preservam a origem e oferecem visão conjunta sem fabricar dados; relatórios continuam corretamente pendentes.
