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

## UI-3.0E2 — Alvos, análises e alertas dos monitores

**Data:** 08/11/2026

**Checkpoint anterior:** `e28925d`

### Modelo operacional

- `monitor_targets` substitui a suposição de que todo alvo é um veículo.
- Alvo `vehicle` referencia `monitoramento.veiculos`; alvo `driver` referencia
  `monitoramento.motoristas`. Uma `CHECK` exige exatamente uma das referências.
- Identificadores legados são preservados somente para reconciliação.
- `monitor_analises` e `monitor_alertas` referenciam o alvo canônico e mantêm os
  IDs, scores, conclusão, severidade, estado e auditoria do operador.
- Nenhuma FK operacional aponta para Tracker ou Dirija Bem.

### Resultado e política de dados falsos

- As 10 atribuições existentes eram Tracker, estavam ativas e possuíam
  correspondência canônica: resultado `vehicle/tracker: 10`.
- Não há atribuições Dirija Bem atuais; o schema e o backfill já suportam
  `CODUSU` como alvo `driver`.
- As quatro linhas de `tracker.monitor_alertas` não têm `analise_id` e são os
  seeds falsos registrados pela auditoria. Permaneceram no legado para
  rastreabilidade e não foram copiadas para a operação real.
- Backfill executado duas vezes sem alterar contagens; zero alvos órfãos.
- Prova MariaDB criou análise e alerta reais temporários, copiou ambos com os
  mesmos IDs/alvo/estado e removeu os registros dos dois schemas por ID.
- Resultado final operacional: 10 alvos, zero análises e zero alertas.
- Runner: `0 migrations pendentes` após migration 013.
- Integração real: `1 passed`.
- Regressão backend: `135 passed, 5 skipped`.
- O runtime permanece no legado até a virada coordenada da UI-3.0E3.

## UI-3.0E3A — Virada do runtime de incidentes

**Data:** 09/11/2026

**Checkpoint anterior:** `8777fb5`

### Alterações

- Listagem, detalhe, transições, comentários, resolução, falsos positivos e
  falsos negativos passaram a ler e escrever exclusivamente em
  `monitoramento.incidents` e `monitoramento.incident_timeline`.
- A fila enriquece o veículo usando identidades e vínculos canônicos, sem JOIN
  com `tracker.veiculo_unificado`.
- Enquanto a lista de veículos estiver em `shadow`, falso negativo aceita o ID
  legado da interface e o converte para o veículo canônico. Em modo
  `operational`, exige diretamente um ID canônico ativo.
- O correlacionador resolve Tracker por `device_id`. Dirija Bem resolve
  motorista por `CODUSU` e, quando houver mais de um veículo histórico, exige a
  placa do evento para evitar atribuição incorreta.
- Evidências conservam `event_source`; `event_id` não cria dependência física
  com a tabela da fonte.

### Evidências

- API real: falso negativo criado com ID legado, convertido para veículo
  canônico, listado e resolvido; HTTP 201/200/200.
- Consulta posterior confirmou zero escrita correspondente em
  `tracker.incidents`.
- Correlação real Tracker e Dirija Bem com placa criou os dois casos no veículo
  canônico esperado; zero escrita do correlacionador no legado.
- Todos os registros temporários foram removidos por ID; ambos os stores ficaram
  com zero incidentes e zero timelines ao final.
- Concorrência/idempotência no store operacional: `3 passed`.
- Regressão backend: `138 passed, 5 skipped`.
- Teste de contrato impede reintroduzir `INSERT/UPDATE` de incidentes no schema
  legado.

## UI-3.0E3B — Virada do runtime de monitores

**Data:** 09/11/2026

**Checkpoint anterior:** `bf7677d`

- CRUD de monitores usa `monitoramento.monitores`.
- Atribuições usam `monitor_targets`; o contrato HTTP legado conserva os nomes
  `veiculomonitor_id`, `veicod_tracker` e `codusu_dirijabem` apenas na borda.
- Análises e alertas usam o alvo canônico e são retornados no formato esperado
  pelo frontend atual.
- Reconhecer, resolver e descartar alertas atualizam somente o store operacional.
- Estatísticas leem exclusivamente monitores, alvos, análises e alertas reais;
  os quatro seeds falsos do legado não aparecem.
- Ciclo MariaDB real criou monitor, associou veículo, salvou análise, criou e
  reconheceu alerta; todas as contagens do legado permaneceram iguais e a
  limpeza por ID removeu os temporários.
- Endpoints reais: 5 monitores, 2 alvos no monitor #1, zero alertas operacionais;
  lista, detalhe, alvos, estatísticas e alertas responderam HTTP 200.
- Testes focais e integração real: `4 passed`.

## UI-3.0F — Identidade operacional como fonte oficial

**Data:** 09/11/2026

**Checkpoint anterior:** `e92f5af`

- `AITRACK_IDENTITY_READ_MODEL` agora assume `operational` quando ausente.
- `AITRACK_IDENTITY_ALLOW_FALLBACK` assume `0`; indisponibilidade operacional
  gera erro explícito em vez de dados legados silenciosos.
- `legacy`, `shadow` e fallback continuam disponíveis somente por configuração
  deliberada para diagnóstico ou rollback.
- A etapa 3.0 foi marcada concluída após a virada de identidade, incidentes,
  monitores, alvos, análises e alertas.
- Sem variáveis de override, `/api/v1/vehicles`, `/api/unified/vehicles`,
  `/api/unified/stats` e `/api/vehicles/unified` responderam HTTP 200 e total 26.
- Testes focais de identidade, APIs e ponte de incidente: `16 passed`.

## UI-3.1 — Cercas compartilhadas e versões geométricas

**Data:** 09/11/2026

**Checkpoint anterior:** `90bf8b8`

- `monitoramento.geofences` armazena identidade pública, nome, regra permitida
  ou proibida, ciclo de vida, proprietário lógico, responsáveis e versão de
  concorrência otimista.
- `monitoramento.geofence_versions` preserva cada desenho com número, hash,
  motivo, autor e intervalo de validade.
- Círculo usa `POINT(longitude latitude)` e `radius_meters`; polígono usa
  `POLYGON` e raio nulo.
- Geometria é `GEOMETRY NOT NULL` com índice espacial. Restrições impedem raio
  ausente em círculo, raio em polígono e validade temporal invertida.
- Versões usam FK restritiva; apagar uma cerca não apaga silenciosamente seu
  histórico.
- Prova MariaDB inseriu versões circular e poligonal, confirmou tipos `POINT` e
  `POLYGON`, raio de 500 m e índice espacial.
- Rollback deixou zero cercas temporárias; runner reportou zero pendências.
- Vínculo com veículo/grupo, agenda e histerese pertencem às próximas tarefas e
  não foram antecipados nesta migration.

## Validação integrada — UI-3.0E3B, UI-3.0F e UI-3.1

**Data:** 09/11/2026

### Testes automatizados

- Backend com todas as integrações MariaDB habilitadas: `151 passed`.
- App 2: `44 passed` em 12 suítes; TypeScript sem erros; build de produção
  compilado com sucesso.
- App 1: build de produção concluído. Há um warning ESLint preexistente de import
  não usado em `MapComponent.tsx`.
- O Jest do App 1 não executa testes porque a configuração antiga do CRA não
  transpila o módulo ESM `react-leaflet`; falha antes de executar qualquer teste.
  O problema é anterior e não está relacionado às mudanças de banco/API.

### Runtime e simuladores

- Backend: PID `1338479`, API 5009 e socket 9000.
- Simulador Tracker: PID `1340359`, 10 veículos enviando; `/api/posicoes`
  retornou 10 posições.
- Simulador Dirija Bem: PID `1340436`, 5 motoristas em viagens contínuas a 10x;
  pontos observados avançando sem exceções.
- App 1: porta 3001, HTTP 200 e compilação de desenvolvimento sem erro.
- App 2: porta 3003, HTTP 200 e polling do backend sem respostas de erro.

### API e reconciliação do banco

- Identidade: quatro endpoints HTTP 200 com 26 veículos operacionais.
- Monitores: 5 configurações, 10 alvos canônicos, 2 alvos no monitor #1.
- Alertas operacionais: zero; os 4 seeds falsos permanecem somente no legado.
- Incidentes operacionais: zero após a limpeza dos testes; nenhuma timeline
  residual.
- Cercas e versões: zero registros após rollback da prova geométrica.
- `tracker.schema_migrations`: 14 arquivos registrados, zero pendentes.
- Logs do backend durante posições Tracker e polling do frontend não mostraram
  exceções; scores dos primeiros ciclos foram calculados normalmente.
