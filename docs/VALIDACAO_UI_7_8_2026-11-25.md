# Validação UI-7.8 — SLA e automação

**Data:** 25/11/2026 01:04 (`America/Sao_Paulo`)

**Checkpoint:** `9533617` · **Implementação:** `38c6f80`

## Resultado

O contrato `operations-metrics.v1` expõe mediana, p95, válidos e excluídos para
detecção, triagem e resolução. SLA separa dentro, em risco, vencido e sem prazo.
Automação informa denominador e distingue simulação de envio; takeover/atribuição
humana, `failed` transitório e `dead` são indicadores separados.

## Evidências

- 5 testes focados; 522 backend e 86 frontend; TypeScript/build aprovados;
- consulta real leu 9.574 incidentes: detecção válida, triagem/resolução ausentes
  corretamente como `null`, SLA vencido conforme os prazos persistidos;
- invariantes: denominador de automação = incidentes e SLA válido + excluído = total;
- `EXPLAIN` inicial revelou scan; migration 060 adicionou `idx_incidents_opened_at`;
- novo `EXPLAIN`: `type=range`, chave temporal dedicada.

## Limitação

A base atual não possui triagem/resolução nos incidentes consultados; a interface
mostra indisponível em vez de transformar ausência em tempo zero.
