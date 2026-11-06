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
  "telemetry": [
    {
      "source": "tracker",
      "mode": "simulation",
      "last_communication_at": "2026-11-06T05:30:00-03:00"
    },
    {
      "source": "dirijabem",
      "mode": "replay",
      "last_communication_at": null
    }
  ],
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
- `telemetry` possui exatamente uma entrada para cada identidade disponível.
- `source` identifica a origem sem confundi-la com `identity_type`.
- `mode` aceita `live`, `simulation`, `replay`, `synthetic` e `unknown`.
- `last_communication_at` usa ISO 8601 ou `null` quando a fonte ainda não disponibiliza o horário.
- Modos ausentes ou inválidos são publicados como `unknown`, nunca presumidos como produção.

## Implementações

- Backend: `aitrackdatadrivr/server/unified_vehicle_dto.py`;
- Frontend: `aitrackdatadrivr/frontend/src/types/unifiedVehicle.ts`;
- Testes: `test_unified_vehicle_dto.py` e `unifiedVehicle.test.ts`.

## Endpoint versionado

`GET /api/v1/vehicles` entrega uma coleção de `vehicle.v1`. Os modos são configurados no backend por `AITRACK_TRACKER_MODE` e `AITRACK_DIRIJABEM_MODE`.

## Compatibilidade

`/api/unified/*` e `/api/vehicles/unified` continuam entregando o formato legado. Nenhum consumidor existente foi migrado ou quebrado.
