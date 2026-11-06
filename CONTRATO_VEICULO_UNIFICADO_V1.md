# Contrato de Veículo Unificado — `vehicle.v1`

Este contrato define uma identidade única sem apagar os identificadores das fontes Tracker e Dirija Bem. Ele foi introduzido de forma aditiva: os endpoints legados permanecem inalterados para não quebrar o App 1.

## Estrutura

```json
{
  "schema_version": "vehicle.v1",
  "vehicle_id": 30,
  "identity_type": "both",
  "display_name": "Veículo executivo",
  "plate": "ABC-1D23",
  "active": true,
  "tracker": {
    "device_id": "DEV-30",
    "veicod": 42
  },
  "dirijabem": {
    "codusu": 614
  }
}
```

## Regras

| `identity_type` | `tracker` | `dirijabem` |
|---|---:|---:|
| `tracker_only` | obrigatório | `null` |
| `app_only` | `null` | obrigatório |
| `both` | obrigatório | obrigatório |

- `vehicle_id` é a identidade interna e deve ser positivo.
- `device_id`, `veicod` e `codusu` nunca são convertidos uns nos outros.
- Ausência de vínculo é representada por `null`, não por identificador inventado.
- Placa é opcional e normalizada para maiúsculas.
- `display_name` é obrigatório e possui fallback determinístico durante a conversão.
- `schema_version` permite evolução sem alterar silenciosamente o contrato.
- Origem da telemetria, modo e última comunicação serão acrescentados na tarefa 1.2; não devem ser inferidos da identidade.

## Implementações

- Backend: `aitrackdatadrivr/server/unified_vehicle_dto.py`;
- Frontend: `aitrackdatadrivr/frontend/src/types/unifiedVehicle.ts`;
- Testes: `test_unified_vehicle_dto.py` e `unifiedVehicle.test.ts`.

## Compatibilidade

Nesta etapa nenhum endpoint foi migrado. `/api/unified/*` e `/api/vehicles/unified` continuam entregando o formato legado. A adoção do DTO deve ocorrer em endpoint versionado ou por campo adicional, seguida de migração explícita dos consumidores.
