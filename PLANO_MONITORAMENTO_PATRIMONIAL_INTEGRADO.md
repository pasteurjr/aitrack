# Especificação e plano — Monitoramento patrimonial integrado AITrack + Dirija Bem

**Data:** 05/11/2026  
**Repositório canônico:** `/home/pasteurjr/progreact/aitrack`  
**Aplicação ativa:** `/home/pasteurjr/progreact/aitrack/aitrackdatadrivr`  
**Fontes obrigatórias:** bancos `tracker` e `dirijabem`

## 1. Objetivo

Incrementar o AITrack/DataDrivr com monitoramento veicular patrimonial e antifurto, totalmente integrado às duas fontes existentes:

- **Tracker:** posições recebidas de rastreadores físicos, com GPS, velocidade, direção, ignição, alimentação e atributos específicos do protocolo;
- **Dirija Bem:** viagens, posições de alta frequência e métricas comportamentais calculadas pelo aplicativo e pelo modelo fuzzy.

Os dois bancos serão monitorados por um único pipeline. O sistema não terá um monitor “Tracker” e outro “Dirija Bem” com comportamentos incompatíveis. Cada posição será transformada em uma observação normalizada, associada a um veículo unificado e analisada pelos mesmos detectores, agentes, políticas e telas.

O resultado esperado é o ciclo operacional:

```text
Tracker ─────┐
             ├─→ observação normalizada → detectores → incidente → agente → ação
Dirija Bem ──┘                                  ↑                       ↓
                                                └── acompanhamento ─────┘
```

## 2. Escopo funcional

Esta frente acrescentará:

- cerca eletrônica circular e poligonal;
- corredor de rota;
- entrada, saída e permanência em cerca;
- desvio de rota;
- movimento não autorizado;
- possível reboque;
- rastreador ou aplicativo offline;
- perda de GPS ou comunicação;
- alimentação removida e bateria baixa;
- uso em horário não autorizado;
- ignição não autorizada quando o Tracker fornecer o sinal;
- estado armado/desarmado;
- cálculo de risco de furto por múltiplas evidências;
- comunicação, confirmação do proprietário e escalonamento;
- acompanhamento completo por agentes de monitoramento.

Bloqueio remoto não faz parte do MVP. Só poderá entrar posteriormente, com hardware compatível, veículo comprovadamente parado, autorização forte e regras de segurança independentes da IA.

## 3. Estado atual relevante

### 3.1 Já existente

- Servidor TCP para rastreadores na porta 9000.
- Parsers Suntech e Queclink ativos; Maxtrack parcialmente implementado.
- Simulador Tracker com 10 veículos e perfis good/moderate/poor.
- Replay, geração sintética e simulação contínua no Dirija Bem.
- API Flask na porta 5009.
- API e tabela de veículo unificado com `device_id`, `codusu` e placa.
- Eventos de aceleração, frenagem, curva e excesso de velocidade.
- Detecção baseada no intervalo real entre posições.
- Score Tracker pela janela móvel de uma hora.
- Métricas comportamentais e score por viagem no Dirija Bem.
- CRUD de monitores, análises e alertas.
- Interface de mapa, veículos, eventos, monitores e alertas.

### 3.2 Parcial

- O Dirija Bem aparece na API e no mapa, mas não alimenta continuamente o mesmo motor de eventos do Tracker.
- O `monitor_engine` existe, mas não é iniciado pelo processo principal.
- O frontend ainda usa mocks em alertas e detalhes de monitores.
- O simulador Tracker ainda usa heading aleatório.
- Eventos em memória não têm limite nem proteção completa para concorrência.
- Persistência de eventos Tracker ainda pode bloquear o recebimento da telemetria.

### 3.3 Ausente

- Cercas e estado por veículo.
- Rotas planejadas e detector de desvio.
- Estado armado/desarmado.
- Detector de reboque e movimento não autorizado.
- Detector de offline, alimentação removida e tamper normalizado.
- Motor de risco de furto.
- Incidentes consolidados.
- Agentes autônomos, fila de ações e comunicação externa.
- Testes ponta a ponta com as duas fontes.

## 4. Dados que serão monitorados

### 4.1 Banco Tracker

O Tracker é a fonte preferencial para telemetria física em tempo real. O modelo normalizado deverá aproveitar, quando disponível:

| Dado | Uso |
|---|---|
| `device_id` | Identidade do rastreador. |
| latitude/longitude | Cerca, rota, movimento e localização ao vivo. |
| timestamp | Ordem, atraso, offline e duração. |
| velocidade | Movimento, velocidade e reboque. |
| heading | Curvas e coerência de rota. |
| ignição | Viagem, ociosidade, reboque e ignição não autorizada. |
| tensão/bateria | Corte de alimentação e bateria baixa. |
| protocolo/alarme | Pânico, tamper, towing e outros eventos nativos quando suportados. |

Campos inexistentes em determinado protocolo deverão ser `null`, nunca inventados.

### 4.2 Banco Dirija Bem — posição contínua

A tabela `localizacaodados` será lida incrementalmente pelo identificador `LOCDADCOD`, mantendo watermark por consumidor. Campos confirmados:

| Campo | Significado | Uso no monitoramento |
|---|---|---|
| `LOCDADCOD` | Identificador crescente do ponto | Watermark e idempotência. |
| `CODVIA` | Viagem | Correlação com motorista, placa e métricas. |
| `DATAHORA` | Horário do ponto | Ordem, atraso e offline. |
| `VELATU` | Velocidade atual | Movimento e excesso de velocidade. |
| `ACELLINATU` | Aceleração linear | Aceleração/frenagem perigosa. |
| `ACELGPSATU` | Aceleração derivada de GPS | Validação e fallback da aceleração. |
| `VARDIRATU` | Variação de direção | Curva agressiva. |
| `coords` | Ponto geográfico | Cerca, rota e localização ao vivo. |

O Dirija Bem não fornece necessariamente ignição física, tensão ou tamper. Esses campos permanecem indisponíveis, exceto quando o mesmo veículo também possuir Tracker.

### 4.3 Banco Dirija Bem — viagem e direção perigosa

A tabela `viagem` contém identidade, período, distância, duração e avaliação comportamental agregada:

| Grupo | Campos | Interpretação |
|---|---|---|
| Identidade | `CODVIA`, `CODUSU`, `PLACA` | Viagem, usuário/motorista e veículo. |
| Período | `DATAHORINI`, `DATAHORFIN` | Início, fim e duração operacional. |
| Exposição | `DISTANCIA`, `DURACAO` | Normalização por tempo e distância. |
| Resultado | `SCORE` | Score final da viagem. |
| Velocidade | `OST`, `OSA`, `OSP` | Tempo, média e pico de excesso de velocidade. |
| Aceleração | `SAM`, `SAA`, `GAM`, `GAA`, `GAP`, `GAN` | Frequência, média e picos positivos/negativos. |
| Direção | `BRP`, `BRM`, `BRA` | Pico e frequência de mudanças de direção moderadas/agressivas. |

Essas métricas não serão descartadas para recalcular tudo apenas pelo Tracker. Elas serão registradas como análise da viagem e convertidas em evidências do incidente:

- `OST`, `OSA`, `OSP` altos → excesso de velocidade recorrente;
- `SAM`, `SAA`, `GAP` altos → aceleração agressiva;
- `GAN` muito negativo → possível frenagem brusca;
- `BRP`, `BRM`, `BRA` altos → curvas ou mudanças agressivas;
- `SCORE` baixo → risco comportamental agregado.

As métricas de viagem complementam os eventos ponto a ponto; não substituem cerca, rota, offline ou antifurto.

## 5. Identidade unificada

O vínculo central será a tabela `veiculo_unificado` no banco Tracker:

```text
vehicle_id interno
├── device_id → tracker.veiculos / tracker.localizacao
├── codusu    → dirijabem.usuario / dirijabem.viagem
└── placa     → dirijabem.veiculo / dirijabem.viagem
```

Regras:

1. Um veículo pode ser `tracker_only`, `app_only` ou `both`.
2. Tracker e Dirija Bem nunca devem criar dois incidentes para o mesmo veículo e período.
3. Se o veículo possuir ambas as fontes, o Tracker fornece sinais físicos e o Dirija Bem fornece contexto de motorista/viagem e métricas comportamentais.
4. Divergências de posição ou identidade devem produzir evento de qualidade de dados, não sobrescrever silenciosamente uma fonte.
5. Toda observação deve manter `source`, `source_record_id` e horário de ingestão.

## 6. Contrato de observação normalizada

As duas fontes deverão produzir o mesmo formato interno:

```json
{
  "vehicle_id": 123,
  "source": "tracker|dirijabem",
  "source_record_id": "string",
  "trip_id": "optional",
  "driver_id": "optional",
  "observed_at": "ISO-8601",
  "received_at": "ISO-8601",
  "latitude": -19.93,
  "longitude": -43.94,
  "speed_kmh": 52.3,
  "heading_deg": 120.0,
  "ignition": true,
  "external_voltage": 13.2,
  "acceleration_ms2": -3.1,
  "heading_change_deg": 48.0,
  "attributes": {}
}
```

Campos não fornecidos serão `null`. O processamento deve ser idempotente por `source + source_record_id`.

## 7. Cerca eletrônica

### 7.1 Tipos

- **Círculo:** centro e raio.
- **Polígono:** área com vários vértices.
- **Corredor:** polyline de rota mais tolerância lateral.
- **Ponto operacional:** origem, destino, cliente, garagem ou parada.

### 7.2 Políticas

- área permitida;
- área proibida;
- estacionamento protegido;
- entrada obrigatória;
- rota planejada;
- horário/calendário;
- tempo máximo ou mínimo de permanência;
- veículos ou grupos associados.

### 7.3 Eventos

- `geofence_enter`;
- `geofence_exit`;
- `geofence_dwell_exceeded`;
- `forbidden_zone_enter`;
- `required_zone_missing`;
- `route_deviation`;
- `route_return`;
- `unexpected_stop`;
- `destination_arrival`.

### 7.4 Proteção contra falso positivo

- margem configurável de 30–50 m;
- duas ou três posições consecutivas;
- tempo mínimo fora/dentro;
- histerese de entrada e saída;
- descarte de salto impossível;
- consideração da precisão GPS quando disponível;
- evento por transição, não por cada posição.

## 8. Monitoramento patrimonial e antifurto

### 8.1 Estado de segurança

Cada veículo terá estado:

- `disarmed`;
- `arming`;
- `armed`;
- `alarm`;
- `stolen_confirmed`;
- `recovery`.

O armamento poderá ser manual, por agenda, ao desligar a ignição ou ao estacionar em cerca protegida.

### 8.2 Detectores

| Detector | Tracker | Dirija Bem | Regra principal |
|---|---:|---:|---|
| Saída de cerca | Sim | Sim | Transição dentro→fora. |
| Entrada proibida | Sim | Sim | Transição fora→dentro. |
| Desvio de rota | Sim | Sim | Distância do corredor acima da tolerância. |
| Movimento armado | Sim | Sim | Deslocamento acumulado acima do limite. |
| Reboque | Sim | Parcial | Movimento com ignição desligada; no app, sem ignição, usar modo armado. |
| Ignição não autorizada | Sim | Não | Ignição ligada enquanto armado. |
| Horário anormal | Sim | Sim | Movimento fora da agenda. |
| Offline | Sim | Sim | Ausência de novos pontos acima do SLA da fonte. |
| Bateria/alimentação | Sim | Não | Tensão baixa ou queda abrupta. |
| Tamper nativo | Depende do hardware | Não | Alarme reportado pelo protocolo. |
| Direção perigosa | Sim | Sim, enriquecido | Eventos Tracker e métricas Dirija Bem. |

### 8.3 Risco de furto

O sistema calculará risco por evidências, sem declarar furto por um único evento:

| Evidência | Peso inicial |
|---|---:|
| Saída de cerca com veículo armado | 30 |
| Movimento com ignição desligada | 35 |
| Ignição não autorizada | 35 |
| Alimentação removida | 25 |
| Tracker offline logo após movimento | 25 |
| Movimento em horário proibido | 15 |
| Desvio de rota | 10 |
| Tamper reportado pelo hardware | 35 |
| Proprietário confirma que não autorizou | Define crítico/confirmado |

Faixas iniciais:

- 0–24: registrar;
- 25–49: atenção;
- 50–74: alto, comunicar;
- 75–100: crítico, comunicar e ligar;
- confirmação do proprietário: `stolen_confirmed`.

Os pesos serão calibrados com simulação e histórico, não tratados como definitivos.

## 9. Atuação do agente

Exemplo de caso:

```text
01:15 veículo armado na garagem
01:17 saída da cerca
01:17 Tracker informa ignição desligada e deslocamento
01:18 tensão externa cai
01:18 risco de furto = 90
01:18 agente envia mensagem com mapa e pede confirmação
01:20 sem resposta: agente liga para o proprietário
01:23 agente aciona contato secundário
01:25 proprietário confirma que não autorizou
01:25 incidente muda para stolen_confirmed
```

O agente deverá:

- explicar as evidências;
- informar localização e última atualização;
- perguntar se o movimento foi autorizado;
- interpretar a resposta;
- acompanhar o veículo;
- escalar por prazo;
- registrar mensagens, ligações e decisões;
- encerrar somente com normalização ou confirmação autorizada.

A IA poderá interpretar e escolher entre ferramentas autorizadas, mas regras determinísticas validarão destinatário, autonomia, cooldown e segurança.

## 10. Modelo de dados novo

Migrations aditivas no banco Tracker:

- `tracking_observations` — observações normalizadas ou referência às fontes;
- `ingestion_watermarks` — último registro processado por fonte;
- `geofences` — geometria GeoJSON e política;
- `geofence_assignments` — veículo/grupo associado;
- `geofence_vehicle_state` — último estado dentro/fora;
- `planned_routes` — rota e tolerância;
- `route_assignments` — rota por veículo/viagem;
- `vehicle_security_state` — armado, alarme e confirmação;
- `tracking_events` — eventos normalizados;
- `incidents` — consolidação de evidências;
- `incident_evidence` — eventos e métricas Dirija Bem/Tracker;
- `agent_actions` — mensagens, ligações e follow-up;
- `agent_audit_log` — decisão e resultado.

O banco Dirija Bem será lido pelo pipeline. Escritas nele continuarão restritas aos simuladores já existentes, evitando modificar o sistema de origem.

## 11. APIs e interface

### 11.1 APIs

- CRUD de cercas;
- associação de cerca a veículo/grupo;
- CRUD de rotas planejadas;
- armar/desarmar veículo;
- consultar estado de segurança;
- eventos por veículo e fonte;
- incidentes e evidências;
- confirmar movimento autorizado/não autorizado;
- posição unificada ao vivo;
- health e lag de cada fonte.

### 11.2 Frontend

- desenhar círculo e polígono no mapa;
- desenhar corredor de rota;
- mostrar veículos dentro/fora;
- mostrar fonte Tracker, Dirija Bem ou ambas;
- botão armar/desarmar;
- timeline de evidências;
- painel de incidentes de furto;
- atraso da última posição;
- posição e rota ao vivo;
- métricas Dirija Bem da viagem;
- ações e respostas do agente.

## 12. Plano de implementação por etapas

Cada tarefa abaixo deve caber em até 30 minutos de execução focada, terminar com teste proporcional e produzir commit/push próprio quando alterar produção.

### Etapa 0 — Segurança e baseline

| ID | Tarefa | Aceite |
|---|---|---|
| P0.1 | Criar checkpoint antes da frente patrimonial | Commit e push identificados. |
| P0.2 | Inventariar colunas Tracker usadas por protocolo | Matriz campo/protocolo versionada. |
| P0.3 | Validar schema Dirija Bem em ambiente somente leitura | Campos e índices confirmados sem escrita. |
| P0.4 | Centralizar configurações e remover credenciais do código | Segredos somente por ambiente. |
| P0.5 | Corrigir/importar runner de migrations idempotente | Dry-run e reaplicação segura. |

### Etapa 1 — Ingestão unificada Tracker + Dirija Bem

| ID | Tarefa | Aceite |
|---|---|---|
| P1.1 | Definir dataclass/schema `TrackingObservation` | Validação cobre campos ausentes. |
| P1.2 | Adaptar posição Tracker ao contrato | Testes Suntech e Queclink. |
| P1.3 | Criar leitor incremental de `localizacaodados` | Watermark por `LOCDADCOD`, sem duplicação. |
| P1.4 | Enriquecer ponto Dirija Bem via `viagem` | `CODUSU`, placa e `CODVIA` disponíveis. |
| P1.5 | Resolver identidade em `veiculo_unificado` | `tracker_only`, `app_only` e `both` testados. |
| P1.6 | Detectar divergência entre fontes | Evento de qualidade sem sobrescrita silenciosa. |
| P1.7 | Criar health/lag por fonte | API mostra último ponto e atraso. |

### Etapa 2 — Cerca eletrônica MVP

| ID | Tarefa | Aceite |
|---|---|---|
| P2.1 | Migration de cercas e associações | Círculo/polígono persistem. |
| P2.2 | Implementar distância geodésica para círculo | Testes dentro, borda e fora. |
| P2.3 | Implementar point-in-polygon | Testes com polígono côncavo e borda. |
| P2.4 | Persistir estado por veículo/cerca | Reinício não perde estado. |
| P2.5 | Gerar `geofence_enter` e `geofence_exit` | Um evento por transição. |
| P2.6 | Adicionar histerese e confirmação por amostras | Ruído na borda não gera rajada. |
| P2.7 | CRUD e associação pela API | Fluxo completo testado. |
| P2.8 | Desenhar e editar cerca no mapa | Geometria salva e recarregada. |

### Etapa 3 — Rotas e eventos patrimoniais

| ID | Tarefa | Aceite |
|---|---|---|
| P3.1 | Migration de rotas e atribuições | Rota por veículo/viagem. |
| P3.2 | Implementar distância ao corredor | Tolerância configurável. |
| P3.3 | Gerar desvio e retorno à rota | Eventos sem duplicação. |
| P3.4 | Detectar parada inesperada e permanência | Agenda e duração consideradas. |
| P3.5 | Detectar offline por SLA da fonte | Tracker e app possuem SLA próprio. |
| P3.6 | Detectar horário não autorizado | Calendário e fuso testados. |
| P3.7 | Detectar tensão baixa/queda de alimentação | Somente quando Tracker fornecer dado. |
| P3.8 | Normalizar alarmes nativos de protocolo | Alarme desconhecido não é inventado. |

### Etapa 4 — Direção perigosa integrada

| ID | Tarefa | Aceite |
|---|---|---|
| P4.1 | Mapear métricas `viagem` para evidências | Todos os campos comportamentais cobertos. |
| P4.2 | Consumir viagem concluída incrementalmente | Uma análise por `CODVIA`. |
| P4.3 | Correlacionar eventos ponto a ponto e score da viagem | Sem dupla penalização. |
| P4.4 | Exibir detalhamento OST/OSA/OSP e aceleração/direção | Tela usa API real. |
| P4.5 | Calibrar score comum Tracker/Dirija Bem | Faixas comparáveis e explicadas. |

### Etapa 5 — Estado armado e risco de furto

| ID | Tarefa | Aceite |
|---|---|---|
| P5.1 | Migration e máquina de estados de segurança | Transições inválidas recusadas. |
| P5.2 | Armar/desarmar manualmente | API auditada. |
| P5.3 | Armamento por cerca/agenda | Testes de horário e garagem. |
| P5.4 | Detectar movimento armado | Distância acumulada e ruído tratados. |
| P5.5 | Detectar reboque com ignição desligada | Apenas Tracker com sinal confiável. |
| P5.6 | Implementar agregador de evidências | Incidente único por episódio. |
| P5.7 | Calcular risco e severidade | Pesos configuráveis e explicáveis. |
| P5.8 | Confirmar autorizado/furto pelo proprietário | Estado e auditoria atualizados. |

### Etapa 6 — Agente e ações

| ID | Tarefa | Aceite |
|---|---|---|
| P6.1 | Integrar incidente ao runtime de agente | Missão e política carregadas. |
| P6.2 | Criar decisão estruturada rule-based | Funciona sem IA externa. |
| P6.3 | Integrar IA externa com JSON validado | Falha retorna ao fallback. |
| P6.4 | Criar fila durável e idempotente | Retry sem ação duplicada. |
| P6.5 | Implementar conector fake de mensagem/ligação | E2E sem contato real. |
| P6.6 | Receber confirmação do proprietário | Resposta associada ao incidente. |
| P6.7 | Implementar follow-up e escalonamento | Prazos e contatos testados. |
| P6.8 | Integrar provedor real em sandbox | Allowlist e limites ativos. |

### Etapa 7 — Operação e frontend sem mocks

| ID | Tarefa | Aceite |
|---|---|---|
| P7.1 | Iniciar workers pelo `run.py` | Health confirma threads/workers. |
| P7.2 | Remover mocks de alertas | Dados reais e estados vazios. |
| P7.3 | Remover mocks do detalhe do monitor | Eventos e veículos reais. |
| P7.4 | Criar console patrimonial | Cerca, armado e incidentes visíveis. |
| P7.5 | Criar timeline multifuente | Origem e evidências identificadas. |
| P7.6 | Adicionar pausa e takeover humano | Ações pendentes controláveis. |

### Etapa 8 — Simulação, testes e homologação

| ID | Tarefa | Aceite |
|---|---|---|
| P8.1 | Corrigir heading do simulador Tracker | Direção segue a rota. |
| P8.2 | Simular entrada/saída de cerca | Evento reproduzível. |
| P8.3 | Simular reboque, corte e offline | Cada cenário gera evidência correta. |
| P8.4 | Simular viagem perigosa Dirija Bem | Métricas entram no incidente. |
| P8.5 | Testar veículo `both` | Incidente único com duas fontes. |
| P8.6 | Executar teste contínuo de 30 minutos | Sem vazamento ou duplicação. |
| P8.7 | Homologar comunicação em allowlist | Nenhum contato não autorizado. |
| P8.8 | Pilotar autonomia nível 1 | Agente recomenda; humano aprova. |
| P8.9 | Evoluir para nível 2/3 após métricas | Autonomia aprovada por evidência. |

## 13. Testes obrigatórios

- unidade: geometria, histerese, rota, offline, risco e estados;
- contrato: adaptadores Tracker e Dirija Bem;
- integração: banco local/mock, watermark e idempotência;
- ponta a ponta: posição → evento → incidente → agente → ação;
- concorrência: duas fontes para o mesmo veículo;
- recuperação: reinício sem perder estado;
- carga: volume equivalente ao `localizacaodados` contínuo;
- segurança: segredo, autorização, limite e auditoria;
- frontend: desenho de cerca e resposta a incidente.

## 14. Cenários de aceite

### Cenário A — Saída da garagem

Veículo armado sai da cerca. Três posições confirmam a saída. O sistema abre um único incidente, informa fonte/evidências e solicita confirmação.

### Cenário B — Veículo com Tracker e Dirija Bem

Tracker e aplicativo reportam o mesmo deslocamento. O sistema associa ambos ao mesmo `vehicle_id`, não duplica incidente e agrega métricas comportamentais da viagem.

### Cenário C — Possível reboque

Tracker informa ignição desligada, mas o veículo se desloca além da tolerância. O risco sobe, o proprietário é notificado e a localização permanece sendo acompanhada.

### Cenário D — Dirija Bem perigoso

A viagem apresenta OST/OSA/OSP e BRA elevados, com score baixo. O sistema cria evidência de direção perigosa, explica os fatores e encaminha ao agente de segurança.

### Cenário E — Fonte offline

Dirija Bem deixa de gerar pontos, mas Tracker continua. O veículo permanece localizável e o sistema registra indisponibilidade somente da fonte. Se ambas pararem após um evento suspeito, o risco aumenta.

## 15. Definition of Done

A frente será considerada pronta quando:

- Tracker e Dirija Bem forem consumidos continuamente e de forma idempotente;
- todo dado estiver associado ao veículo unificado;
- cercas circulares e poligonais funcionarem com histerese;
- rotas e desvios funcionarem nas duas fontes;
- direção perigosa do Dirija Bem estiver integrada aos incidentes;
- estado armado e risco de furto estiverem auditados;
- um incidente agregar evidências sem duplicação;
- agente comunicar, acompanhar e escalar em ambiente homologado;
- frontend não usar mocks nos fluxos patrimoniais;
- testes unitários, integração e ponta a ponta passarem;
- nenhuma credencial estiver versionada;
- nenhuma ação de bloqueio puder ser disparada livremente pela IA.

## 16. Referências técnicas da pesquisa

- [Traccar — Geofences](https://www.traccar.org/geofences/)
- [Traccar — Events and Notifications](https://www.traccar.org/events/)
- [Google Maps — Geofencing architecture](https://developers.google.com/maps/architecture/navsdk-client-side-geofences)
- [Google Maps — Geometry Library](https://developers.google.com/maps/documentation/javascript/geometry)
- [Samsara — Alert Configurations](https://developers.samsara.com/reference/getconfigurations)
- [Samsara — Webhooks](https://developers.samsara.com/docs/webhooks)
- [Geotab — Rule conditions](https://developers.geotab.com/myGeotab/apiReference/objects/ConditionType/index.html)

