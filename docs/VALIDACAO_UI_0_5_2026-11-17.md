# Validação — UI-0.5: base URL e cliente HTTP centralizados

**Executada em:** 17/11/2026 11:11 (`America/Sao_Paulo`)  
**Etapa:** 8 de 74  
**Implementação original:** `fa885d4`

## Resultado esperado

O App 2 deve resolver a base da API em um único ponto configurável e realizar chamadas ao backend somente pelo cliente/serviços compartilhados.

## Resultado obtido

- `src/config/api.ts` resolve `REACT_APP_API_BASE_URL`, remove barras finais e mantém o backend local somente como default de desenvolvimento.
- `src/services/apiService.ts` é o único módulo de produção que importa Axios e instancia `apiClient`.
- Componentes usam serviços de domínio (`fleetService`, `monitorService`, `eventService`, `incidentService`, `geofenceService` e demais), sem montar endereços do backend.
- A URL absoluta do OpenStreetMap em `MapComponent` é um serviço de tiles, não uma chamada à API operacional, e permanece fora deste contrato.

## Evidências

- Busca estática: nenhum import de Axios fora de `apiService.ts`.
- Busca estática: nenhum `localhost:5009` em componentes.
- Testes de configuração e fronteira: **4 aprovados**.
- TypeScript: aprovado.

## Limitações

- O default local continua em `config/api.ts` para desenvolvimento; produção deve definir `REACT_APP_API_BASE_URL` no build.
- A etapa seguinte endurece o teste para impedir regressões por URL absoluta/IP em componentes novos.

## Conclusão

**Aprovada.** A pendência era documental; a centralização histórica continua válida no código atual.
