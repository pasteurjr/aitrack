# Validação UI-7.6 — normalização por exposição

**Data:** 25/11/2026 00:56 (`America/Sao_Paulo`)

**Checkpoint:** `37bbf19` · **Implementação:** `fe5deef`

## Esperado e obtido

Esperado: apresentar eventos por 100 km e por hora dirigida, sem confundir falta de
telemetria com ausência de eventos. Obtido: buckets `exposure-v1` no banco
`monitoramento`, com distância, segundos dirigindo, pontos válidos/descartados,
cobertura e qualidade. Segmentos com lacuna maior que 5 minutos, ordem inválida ou
velocidade inferida acima de 220 km/h são descartados. Denominador zero gera `null`.

## Evidências

- migration 058 aplicada/idempotente, sem escrita em Tracker ou Dirija Bem;
- 9 testes focados; 515 backend e 86 frontend; TypeScript/build aprovados;
- prova transacional: Tracker = 25 km, 7.200 s, cobertura 95,2%, qualidade parcial;
- a mesma resposta marcou Dirija Bem `unavailable`, sem taxa inventada;
- rollback final deixou zero bucket de validação.

## Limitação

O schema, cálculo e consumo estão prontos, mas o materializador contínuo ainda deve
ser conectado ao ciclo operacional de cada fonte. Até lá, a interface informa
indisponibilidade em vez de simular exposição.
