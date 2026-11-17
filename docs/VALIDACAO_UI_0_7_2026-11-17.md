# Validação — UI-0.7: matriz tela, endpoint, fonte e modo

**Executada em:** 17/11/2026 11:20 (`America/Sao_Paulo`)  
**Etapa:** 10 de 74  
**Documento:** `MATRIZ_INTERFACE_ENDPOINTS_FONTES.md`

## Resultado esperado

Cada bloco visual deve declarar endpoint, fonte, modo/proveniência, efeito colateral e comportamento em erro, conferidos contra o código atual.

## Resultado obtido

A matriz histórica foi reescrita porque ainda descrevia detalhes de monitor, alertas e catálogo como mocks e cercas como inexistentes. A nova versão cobre:

- selo de ambiente consultado no runtime;
- frota e identidade Tracker/Dirija Bem;
- dashboard, mapa, timeline e análises;
- monitores e eventos persistidos do detalhe;
- fila real de incidentes e sua timeline;
- cercas circulares/poligonais, atribuições e estado ao vivo;
- capacidades ainda ausentes: sensores, runtime autônomo de IA e comunicação externa;
- riscos que permanecem explícitos, inclusive fallback visual `85` no mapa e início de replay pelo seletor legado Dirija Bem.

## Evidências

- Comparação com as seis abas de `App.tsx`.
- Comparação com todas as rotas declaradas em `apiService.ts`.
- Comparação com blueprints e consultas aos schemas `tracker`, `dirijabem` e `monitoramento`.
- Verificador local confirmou todos os marcadores obrigatórios e nenhum marcador obsoleto.
- Endpoints reais responderam HTTP 200: runtime, veículos v1, monitores, catálogo de eventos, incidentes e estado ao vivo das cercas.

## Limitações

- A matriz registra o estado observado nesta revisão; a regra exige atualização no mesmo commit de futuras mudanças de fonte ou endpoint.
- A presença de um serviço no cliente não significa fluxo completo na interface; essa distinção permanece documentada.

## Conclusão

**Aprovada.** A matriz volta a representar o código e a operação atuais, sem tratar funcionalidades pendentes como concluídas.
