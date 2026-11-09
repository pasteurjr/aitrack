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

## UI-3.2 — Grupos, vínculos e agendas de cerca

**Data:** 09/11/2026

**Checkpoint anterior:** `8e288cf`

- `monitoring_groups` cria grupos operacionais sem depender das fontes.
- `monitoring_group_members` aceita veículo ou motorista canônico e exige
  exatamente uma referência por membro.
- `geofence_assignments` vincula uma cerca a exatamente um veículo, motorista
  ou grupo.
- Cada vínculo possui fuso, período de vigência, notificações de entrada/saída,
  permanência, histerese, cooldown, prioridade, autoria e versão.
- `geofence_assignment_schedules` aceita múltiplas janelas por dia da semana e
  representa explicitamente intervalos que atravessam meia-noite.
- Ausência de janelas significa funcionamento contínuo dentro da vigência; essa
  regra será consumida pelo avaliador da UI-3.9.
- Prova MariaDB atribuiu uma cerca aos três tipos de alvo, criou grupo com
  veículo e motorista e validou janelas `08:00–18:00` e `22:00–06:00`.
- Rollback deixou zero grupos, membros, vínculos ou agendas temporários.
- Migration 015 aplicada; runner com zero pendências.
- Regressão backend: `151 passed, 6 skipped`.

## UI-3.3 — API operacional de cercas

**Data:** 09/11/2026

**Checkpoint anterior:** `f670cd7`

- `GET /api/geofences` lista cercas com paginação, busca e filtros validados de
  estado e regra; `GET /api/geofences/<id-ou-uuid>` devolve o desenho vigente.
- `POST /api/geofences` cria a identidade e a primeira versão geométrica na
  mesma transação, com autor e motivo de mudança auditáveis.
- O contrato usa GeoJSON para polígono e `Circle` com centro
  `[longitude, latitude]` e raio em metros. O banco recebe somente WKT
  parametrizado e conserva um hash SHA-256 canônico do desenho.
- Validação rejeita latitude/longitude fora do domínio, números não finitos,
  raio zero ou acima de 100 km, polígonos abertos, sem área, com pontos
  consecutivos iguais, mais de 500 pontos ou auto-interseção.
- Alteração de desenho e arquivamento/exclusão não foram antecipados: pertencem
  à UI-3.6, quando serão protegidos por versão otimista e vínculos existentes.
- Testes focais: `24 passed`. Integração MariaDB: criação, listagem e detalhe de
  círculo e polígono passaram; limpeza por IDs temporários deixou zero resíduos.
- Regressão completa, com integrações MariaDB habilitadas: `171 passed`.

## UI-3.4 e UI-3.5 — Desenho visual de círculos e polígonos

**Data:** 09/11/2026

**Checkpoint anterior:** `79a0350`

- O mapa ganhou um painel recolhível de criação de cercas, sem dependência nova.
- Círculo é desenhado com dois cliques: centro e borda. O raio é calculado pelo
  Leaflet em metros e mostrado antes da gravação.
- Polígono é desenhado por vértices, com prévia, contagem, desfazer último ponto
  e conclusão explícita. O frontend fecha o anel antes de chamar a API.
- `Esc`, cancelar e refazer evitam que um desenho incompleto seja persistido.
  Salvar fica bloqueado enquanto o desenho ainda está em andamento.
- Área permitida aparece em azul e área proibida em vermelho; rascunhos e
  inativas usam cinza e linha tracejada. A semântica de alerta é explicada no
  próprio seletor.
- Durante o desenho, marcadores e linhas existentes deixam de capturar cliques,
  mas continuam visíveis; zoom e movimentação do mapa permanecem disponíveis.
- A conversão é feita somente na borda HTTP: Leaflet usa `[latitude, longitude]`
  e a API recebe GeoJSON em `[longitude, latitude]`. O navegador não acessa o
  banco e não produz WKT.
- App 2: `47 passed` em 13 suítes; TypeScript sem erros; build de produção
  compilado com sucesso.
- Playwright real, viewport 1440×900: painel mediu 350×588 px, sem erros de
  console; polígono de quatro vértices e círculo de 3,50 km foram persistidos e
  consultados no MariaDB. Limpeza por ID deixou zero cercas de teste.

## UI-3.6 — Edição versionada e arquivamento seguro

**Data:** 09/11/2026

**Checkpoint anterior:** `c708ffd`

- `PUT /api/geofences/<id-ou-uuid>` exige `expected_version`, operador e motivo.
  Versão divergente retorna HTTP 409 e não sobrescreve trabalho concorrente.
- Alteração geométrica encerra a validade da versão anterior e insere uma nova;
  alteração apenas cadastral incrementa a versão da cerca sem duplicar desenho.
- O hash geométrico permanece indexado, mas deixou de ser único para permitir
  retorno deliberado a um desenho histórico como uma nova versão auditável.
- A migration 016 criou `geofence_audit_log`, com ações de criação, atualização,
  redesenho e arquivamento, versões anterior/nova, operador, motivo e detalhes.
- `DELETE /api/geofences/<id-ou-uuid>` não executa exclusão física: muda o estado
  para `archived`. A operação é bloqueada quando existem atribuições ativas.
- A interface permite selecionar uma cerca, alterar metadados, redesenhar como
  círculo ou polígono, restaurar o desenho original e arquivar com confirmação.
  Exibe versões e quantidade de atribuições antes da decisão.
- Integração MariaDB provou versão geométrica 1→2, conflito de escrita obsoleta,
  bloqueio com uma atribuição ativa e arquivamento 2→3 após desativá-la. O log
  registrou `created`, `geometry_updated` e `archived`; rollback deixou zero
  resíduos.
- Playwright executou criação, redesenho círculo→polígono e arquivamento pela
  interface real, sem erros de console; a geometria permaneceu no histórico.
- Regressão completa: `182 passed` no backend com integrações MariaDB e
  `49 passed` no App 2; TypeScript e build de produção passaram.
- Runner registrou a migration 016 e reportou zero pendências; zero auditorias
  órfãs e zero registros temporários da UI-3.6 permaneceram no banco.

## UI-3.7 — Atribuição a veículos, motoristas e grupos

**Data:** 09/11/2026

**Checkpoint anterior:** `cfa4730`

- A API lista alvos exclusivamente da identidade canônica em `monitoramento`:
  veículos ativos não mesclados, motoristas ativos e grupos operacionais.
- Uma cerca aceita vínculo com exatamente um veículo, motorista ou grupo. Para
  área permitida, a atribuição nasce notificando saída; para área proibida,
  notificando entrada.
- Repetir um vínculo ativo retorna conflito. Um vínculo removido é desativado,
  preserva sua versão e pode ser reativado sem furar as chaves únicas.
- Remoção exige a versão esperada do vínculo, impedindo que dois operadores
  sobrescrevam a mesma atribuição silenciosamente.
- Grupos podem ser criados na própria tela com veículos e/ou motoristas; seus
  membros usam IDs canônicos e não IDs particulares de Tracker ou Dirija Bem.
- A interface mostra alvos atuais, tipo, contagem, criação de grupo e remoção.
  A contagem da cerca é atualizada imediatamente e continua bloqueando seu
  arquivamento enquanto houver qualquer atribuição ativa.
- Integração MariaDB criou grupo misto, atribuiu a mesma cerca aos três tipos de
  alvo, rejeitou duplicidade, desativou e reativou o veículo com versão 1→2→3.
- Playwright real criou cerca ativa, atribuiu veículo, criou grupo inline e o
  atribuiu à cerca; o banco confirmou ambos os vínculos e não houve erro de
  console. A limpeza por IDs deixou zero cercas, grupos, membros ou vínculos de
  teste.
- Regressão final: `187 passed` no backend com integrações MariaDB, `50 passed`
  no App 2, TypeScript sem erros e build de produção compilado com sucesso.
- Runner permaneceu com zero migrations pendentes; reconciliação confirmou zero
  cercas/grupos de teste e zero vínculos órfãos.

## UI-3.8 — Entrada e saída com histerese

**Data:** 09/11/2026

**Checkpoint anterior:** `b8e49ee`

- A migration 017 criou estado persistente por atribuição e alvo canônico, além
  do histórico imutável de cruzamentos em `monitoramento`. As duas estruturas
  referenciam somente identidades, cercas e versões geométricas operacionais.
- O mesmo motor resolve posições Tracker por `device_id`/`VEICOD` e posições
  Dirija Bem por `CODUSU`/placa, incluindo o vínculo temporal entre veículo e
  motorista quando existe. Atribuições diretas e por grupo são respeitadas.
- Círculos e polígonos usam distância assinada à borda. A classificação só muda
  fora da banda de histerese do vínculo (30 m por padrão) e requer duas amostras
  consecutivas. A primeira amostra confiável define a linha de base sem alerta.
- Pacote repetido ou fora de ordem é ignorado. Permanecer no mesmo lado não
  duplica evento; ruído que retorna ao estado estável cancela a confirmação em
  andamento. O número de amostras pode ser configurado por
  `GEOFENCE_CONFIRMATION_SAMPLES`.
- Identidade, vínculo e geometria aplicáveis usam cache de 60 segundos
  (`GEOFENCE_CACHE_TTL_SECONDS`), inclusive quando o alvo não possui cerca,
  evitando consultar o catálogo remoto a cada pacote sem atrasar mudanças por
  mais de um minuto.
- Cada evento conserva fonte, alvo, cerca, versão geométrica, regra, sentido do
  cruzamento, horário, coordenadas, precisão disponível e distância da borda.
  Agenda/permanência e correlação com incidente continuam isoladas nas UI-3.9 e
  UI-3.10, respectivamente.
- O caminho de ingestão Tracker e os dois fluxos Dirija Bem (contínuo e replay)
  chamam o motor após persistirem a posição; falha na cerca é isolada e não
  interrompe a telemetria de origem.
- Testes unitários cobriram círculo, polígono, borda, histerese, confirmação,
  ruído e não duplicidade. A integração MariaDB criou uma área permitida para
  Tracker e uma proibida para Dirija Bem, confirmou exatamente uma saída e uma
  entrada e limpou estado, eventos, vínculos, versões e cercas temporárias.
- Regressão final com integrações MariaDB: `204 passed`. Runner: zero migrations
  pendentes.
