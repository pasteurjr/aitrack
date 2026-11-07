# Validações da Etapa 3

## UI-3.0A — Modelo operacional unificado

**Data:** 06/11/2026

**Commit:** `e52da8e`

- Definido `monitoramento` como schema operacional comum.
- Separadas identidades de veículos e motoristas. `CODUSU` do Dirija Bem passa
  a ser identidade de motorista, não identidade de veículo.
- Tracker e Dirija Bem permanecem sistemas-fonte e não recebem FKs da camada
  operacional.
- Migration 010 coberta por quatro testes estruturais.
- Regressão antes da aplicação: `103 passed, 3 skipped`.

## UI-3.0B — Runner e implantação inicial

**Data:** 06/11/2026

**Checkpoint anterior:** `e52da8e`

### Segurança do runner

- Descoberta determinística das migrations por número e nome.
- Baseline 001–009 só é registrado depois da confirmação das tabelas e colunas
  existentes no banco.
- Nome e SHA-256 de cada arquivo aplicado ficam em
  `tracker.schema_migrations`; alteração posterior de migration aplicada causa
  erro explícito.
- O cliente MariaDB recebe credenciais por arquivo temporário com modo `0600`,
  removido mesmo em caso de falha; a senha não aparece na linha de comando.
- `--dry-run` não cria tabela nem registra baseline.

### Aplicação e evidências

- Servidor confirmado: MariaDB `10.3.39`.
- A migration `010_create_unified_operational_identity.sql` foi aplicada com
  sucesso.
- `monitoramento` possui seis tabelas: fontes, veículos, identidades de veículo,
  motoristas, identidades de motorista e vínculos temporais.
- Fontes `tracker` e `dirijabem` cadastradas como somente leitura.
- Dez arquivos registrados no histórico: baseline legado mais migration 010.
- Segunda execução em dry-run: `0 migrations pendentes`.
- Regressão posterior: `108 passed, 3 skipped`.
- Nenhuma cópia de dados ou mudança nas APIs ocorreu nesta etapa; as tabelas de
  identidade permanecem vazias até a UI-3.0C.

## UI-3.0C — Backfill da identidade operacional

**Data:** 06/11/2026

**Checkpoint anterior:** `01649e9`

### Regras aplicadas

- Placas são normalizadas para maiúsculas e caracteres alfanuméricos antes da
  resolução da identidade.
- `device_id`, `VEICOD` e placa do Tracker viram identidades do veículo.
- `CODUSU` vira identidade do motorista Dirija Bem; nunca é gravado como ID de
  veículo.
- Cada placa encontrada nas viagens Dirija Bem referencia um veículo canônico.
- Relações usuário–placa são gravadas como vínculos temporais, usando a primeira
  e a última viagem observadas.
- UUIDs v5 determinísticos e chaves únicas tornam o processo reexecutável.

### Resultado medido

- Fonte legada: 10 veículos Tracker e 10 usuários Dirija Bem.
- Histórico Dirija Bem: 27 pares usuário–placa, sobre 16 placas distintas.
- Destino: 26 veículos, 46 identidades veiculares, 10 motoristas, 10 identidades
  de motorista e 27 vínculos temporais.
- Distribuição veicular: 16 placas Dirija Bem; 10 dispositivos, 10 `VEICOD` e 10
  placas Tracker.
- O backfill foi executado duas vezes e todas as contagens permaneceram iguais.
- Verificações: zero identidade órfã, zero vínculo órfão, zero UUID duplicado e
  zero identidade de origem duplicada.
- Runner: `0 migrations pendentes` após aplicação da migration 011.
- Regressão backend: `112 passed, 3 skipped`.
- Compatibilidade: `/api/monitors` e `/api/unified/vehicles` responderam HTTP 200;
  eles continuam lendo o legado até a troca controlada da UI-3.0D.

## UI-3.0D — Dupla leitura e fallback controlado

**Data:** 07/11/2026

**Checkpoint anterior:** `6b3ca1e`

### Estratégia

- `AITRACK_IDENTITY_READ_MODEL=legacy`: consulta somente
  `tracker.veiculo_unificado`.
- `AITRACK_IDENTITY_READ_MODEL=shadow` (padrão): consulta os dois modelos,
  registra a comparação e devolve o legado para preservar IDs e contratos.
- `AITRACK_IDENTITY_READ_MODEL=operational`: devolve `monitoramento`; se a
  consulta falhar, volta ao legado apenas quando
  `AITRACK_IDENTITY_ALLOW_FALLBACK=1`.
- O modo operacional não foi ativado permanentemente porque incidentes e
  atribuições de monitor ainda referenciam os IDs antigos. Essa troca pertence à
  UI-3.0E.

### Cobertura e evidências

- Comparação real: legado 20, operacional 26, 20 placas comuns, zero placa
  ausente no operacional e 6 veículos exclusivos do histórico Dirija Bem.
- Em `shadow`: `/api/v1/vehicles`, `/api/unified/vehicles` e
  `/api/unified/stats` retornaram HTTP 200 e total 20.
- Em `operational`, somente para validação isolada: `/api/v1/vehicles` retornou
  HTTP 200 e total 26.
- APIs versionada e legada passaram a usar o mesmo seletor de read model.
- A consulta de veículos vinculados a monitores permanece legada até a migração
  das atribuições, evitando mistura de IDs.
- Testes cobrem shadow, operacional, fallback habilitado, fail-closed, comparação
  de cobertura e os contratos da API legada.
- Regressão backend: `122 passed, 3 skipped`.

## UI-3.0E1 — Estrutura e backfill de incidentes

**Data:** 07/11/2026

**Checkpoint anterior:** `01a7b0d`

### Estrutura operacional

- Criadas `monitoramento.monitores`, `monitoramento.incidents` e
  `monitoramento.incident_timeline`.
- Incidentes referenciam `monitoramento.veiculos.id` como identidade oficial e
  guardam `legacy_vehicle_id` para reconciliação e rollback.
- Timeline preserva IDs, idempotência, atores, causalidade e horários.
- `event_id` mantém a referência lógica acompanhada por `event_source`, sem FK
  para `tracker.eventos`; a camada operacional não depende fisicamente da fonte.
- Nenhuma tabela de `tracker` ou `dirijabem` foi alterada.

### Backfill e evidências

- Os 5 monitores-base foram copiados com os mesmos IDs.
- A origem possuía zero incidentes e zero entradas de timeline no momento do
  corte; a execução repetida manteve as mesmas contagens.
- Prova MariaDB criou um incidente temporário com timeline no legado, executou o
  backfill e confirmou no destino: mesmo ID, mesmo monitor, mesma chave
  idempotente e veículo canônico correspondente.
- Limpeza explícita por ID deixou zero registros `ui30e1:%` nos dois schemas.
- Runner após migration 012: `0 migrations pendentes`.
- Integração real: `1 passed`.
- Regressão backend: `129 passed, 4 skipped`.
- O runtime ainda escreve no legado. A troca de leitura/escrita ocorrerá somente
  depois da migração das atribuições na UI-3.0E2.
