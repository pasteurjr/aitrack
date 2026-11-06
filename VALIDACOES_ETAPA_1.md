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

## UI-1.4 — Cabeçalho contextual do veículo

**Data:** 06/11/2026
**Checkpoint anterior:** `0f93f4c`

### Validações automatizadas

- Frontend: `35 passed` em 11 suítes.
- Testes novos: ausência de seleção, identidade Tracker, identidade sem vínculo, fechamento e falha da API.
- TypeScript: `npx tsc --noEmit` sem erros.
- Build de produção: concluído com sucesso.
- `git diff --check`: sem erros de whitespace.

### Validação operacional com navegador automatizado

| Verificação | Resultado |
|---|---:|
| frontend | HTTP 200 |
| pesquisa utilizada | `SIM-1000` |
| itens visíveis após pesquisa | 1 |
| identidade resolvida | Veículo simulado rastreador GPS 1 |
| procedência | `TRACKER` |
| modo retornado | `unknown` |
| último contato retornado | não informado |
| cabeçalho após fechar | removido |
| erros de página | 0 |
| requisições falhas | 0 |

O cabeçalho usa o mesmo contrato versionado da frota unificada e fica acima do
mapa durante a seleção. Nenhum score, modo ou horário ausente é fabricado. A
captura da prova visual foi gerada em
`/tmp/aitrack-ui-1.4-vehicle-header.png` durante a validação local.

## UI-1.5 — Episódio de excesso de velocidade

**Data:** 06/11/2026
**Checkpoint anterior:** `562a313`

### Contrato implementado

- O episódio inicia no primeiro pacote acima de 80 km/h.
- Pacotes seguintes acima do limite não criam novos eventos.
- O detector rearma somente abaixo de 75 km/h.
- Cada início recebe `episode_id` determinístico e `episode_state: started`.
- Estado independente por veículo e protegido por lock.
- Persistência no banco ocorre fora do lock do motor.

### Evidências

- Teste de condição contínua: um único evento.
- Teste de recuperação abaixo de 75 km/h: novo episódio permitido.
- Teste na fronteira de 75 km/h: detector permanece armado e não duplica.
- Teste focal: `8 passed`.
- Suíte completa do backend: `24 passed`.
- Compilação dos módulos Python: sem erros.
- O `.venv` descrito no handoff ainda não existe; nenhum pacote foi instalado
  no Python global e a suíte foi executada com o interpretador já configurado.

## UI-1.6 — Cooldown e histerese dos demais detectores

**Data:** 06/11/2026
**Checkpoint anterior:** `a9a229f`

### Contrato implementado

- Aceleração, frenagem e curva brusca emitem um evento por episódio.
- Liberação exige queda para 60% do limiar de ativação.
- Novo episódio só pode ser emitido após cooldown configurável, padrão 30 s.
- Estado e cooldown são independentes por veículo e tipo de detector.
- Eventos recebem `episode_id` e `episode_state: started`.

### Evidências

- Condição sustentada não duplica evento.
- Liberação seguida de reativação rápida é suprimida.
- Liberação após cooldown permite novo episódio.
- Os três detectores transitórios carregam os metadados do episódio.
- Teste focal do motor: `11 passed`.
- Suíte completa do backend: `27 passed`.
- Compilação dos módulos Python: sem erros.
