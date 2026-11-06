# Validações — Etapa 1: Eventos e Identidade

## UI-1.2 — Procedência, modo e última comunicação

**Data:** 06/11/2026  
**Checkpoint anterior:** `2960557`

### Validações automatizadas

- Backend: `22 passed`.
- Frontend: `29 passed`.
- TypeScript: sem erros.
- Build de produção: concluído sem warnings de código.

### Validação operacional

O backend foi reiniciado e `GET /api/v1/vehicles` foi consultado contra o banco atual, somente leitura:

| Verificação | Resultado |
|---|---:|
| contrato | `vehicle.v1` |
| veículos | 20 |
| `tracker_only` | 10 |
| `app_only` | 10 |
| fonte Tracker | 10 |
| fonte Dirija Bem | 10 |
| modo `unknown` | 20 |
| última comunicação `null` | 20 |

O resultado `unknown`/`null` é intencional e seguro: as fontes atuais ainda não fornecem modo e última comunicação ao cadastro unificado. O endpoint não presume produção, simulação ou horário inexistente. Os modos poderão ser configurados por `AITRACK_TRACKER_MODE` e `AITRACK_DIRIJABEM_MODE`; horários serão preenchidos quando os adaptadores de fonte entregarem essa informação.

### Compatibilidade

- Novo endpoint aditivo: `GET /api/v1/vehicles`.
- APIs legadas não foram alteradas.
- App 1 não foi migrado nem afetado.

## UI-1.3 — Lista unificada pesquisável

**Data:** 06/11/2026  
**Checkpoint anterior:** `e170bab`

### Validações automatizadas

- Frontend: `30 passed`.
- TypeScript: sem erros.
- Build de produção: concluído com sucesso.
- Testes cobrem filtro por fonte, pesquisa, resultado vazio e seleção.

### Validação operacional com Playwright

| Verificação | Resultado |
|---|---:|
| endpoint `GET /api/v1/vehicles` | HTTP 200 |
| total exibido | 20 |
| pesquisa utilizada | `614` |
| itens visíveis após pesquisa | 1 |
| erros de página | 0 |

A lista passou a consumir a identidade versionada. A pesquisa encontra placa, nome, `device_id` e `codusu`; modo e última comunicação são apresentados explicitamente, inclusive quando `unknown`/`null`.
