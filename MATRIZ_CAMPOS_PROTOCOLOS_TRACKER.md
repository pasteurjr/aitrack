# P0.2 — Matriz de campos dos protocolos Tracker

**Data da auditoria:** 05/11/2026  
**Baseline:** `f9dbcc1`  
**Código ativo:** `aitrackdatadrivr/server/`  
**Escopo:** comportamento efetivamente implementado; não representa toda a capacidade dos equipamentos físicos.

## 1. Fluxo auditado

```text
pacote TCP :9000
  → protocol_parsers.parse_data()
  → socket_server.handle_connection()
  → db_handler.save_location()
  ├─→ tracker.localizacao
  └─→ behavioral_engine.add_position()
```

Arquivos auditados:

- `server/protocol_parsers.py`;
- `server/socket_server.py`;
- `server/db_handler.py`;
- `server/behavioral_engine.py`;
- `simulator.py`;
- `tests/test_protocol_parsers.py`.

## 2. Identificação dos protocolos

| Protocolo | Identificação atual | Estado no simulador | Observação |
|---|---|---|---|
| Maxtrack | pacote iniciado por `>REV` | Desativado no fluxo principal | Pacote real não contém `device_id` no formato implementado. Prefixo opcional `device_id|` existe apenas para simulação/integração controlada. |
| Suntech | pacote iniciado por `ST` | Ativo | `device_id` vem no campo 2. A identificação `ST` é ampla e deve futuramente validar o modelo/tipo de mensagem. |
| Queclink | pacote iniciado por `+RESP:GTRIC` | Ativo | Somente a mensagem `GTRIC` é aceita atualmente. Outros eventos Queclink não são reconhecidos. |

## 3. Campos produzidos pelo parser

Legenda:

- **Real:** valor extraído do pacote;
- **Fixo:** valor inventado/fixado pelo parser;
- **Ausente:** retornado como `None` ou não suportado;
- **Condicional:** depende de prefixo ou formato específico.

| Campo normalizado atual | Maxtrack | Suntech | Queclink | Observação |
|---|---|---|---|---|
| `protocol` | Real (`maxtrack`) | Real (`suntech`) | Real (`queclink`) | Produzido pelo parser, mas não persistido em `localizacao`. |
| `device_id` | Condicional | Real | Real | Maxtrack sem prefixo vira anônimo. |
| `timestamp` | Real | Real | Real | Convertido para ISO string sem timezone. |
| `gps_status` | Real (`A`) | Fixo `True` | Fixo `True` | Suntech e Queclink não leem status real no formato atual. |
| `latitude` | Real | Real | Real | Persistido como POINT. |
| `longitude` | Real | Real | Real | Persistido como POINT. |
| `speed` | Real | Real | Real | Persistido e enviado ao motor comportamental. |
| `heading` | Real | Real | Real | Persistido como `ORIENT` e enviado ao motor. |
| `ignition` | Real | Real | Real | Extraído, mas descartado antes da persistência/análise. |
| `battery_voltage` | Real | Real | Real | Extraído, mas descartado antes da persistência/análise. |
| `panic` | Fixo `False` | Fixo `False` | Fixo `False` | Não existe detecção de pânico implementada. |
| `altitude` | Ausente | Ausente | Real | Persistido somente quando fornecido. |

## 4. Mapeamento de campos por posição no pacote

### 4.1 Maxtrack `REV01`

| Índice | Conteúdo usado |
|---:|---|
| 1 | data `ddMMyy` |
| 2 | hora `HHmmss` |
| 3 | status GPS (`A`) |
| 4 | latitude |
| 5 | longitude |
| 6 | velocidade |
| 7 | heading |
| 8 | ignição |
| 9 | tensão |

Limitação crítica: o formato implementado não fornece identidade no corpo. Todos os pacotes reais sem prefixo são consolidados em `MAXTRACK-ANON`, misturando equipamentos distintos.

### 4.2 Suntech `ST310U`

| Índice | Conteúdo usado |
|---:|---|
| 1 | `device_id` |
| 3 | data `yyyyMMdd` |
| 4 | hora `HH:mm:ss` |
| 5 | latitude |
| 6 | longitude |
| 7 | velocidade |
| 8 | heading |
| 9 | ignição |
| 11 | tensão |

Os demais campos presentes no pacote simulado — GPS, bateria interna, rede e identificadores celulares — não são normalizados.

### 4.3 Queclink `GTRIC`

| Índice | Conteúdo usado |
|---:|---|
| 1 | `device_id` |
| 6 | data `ddMMyy` |
| 7 | hora `HHmmss` |
| 8 | latitude |
| 9 | longitude |
| 10 | velocidade |
| 11 | heading |
| 12 | ignição |
| 14 | tensão |
| último | altitude |

Limitação: alarmes Queclink de reboque, tamper, pânico, alimentação, geofence e demais mensagens `+RESP:*` não passam pelo identificador atual, que aceita somente `+RESP:GTRIC`.

## 5. O que é persistido hoje

Tabela `tracker.localizacao`:

| Campo do parser | Destino | Estado |
|---|---|---|
| `latitude` + `longitude` | `LOCLATLONG` | Persistido. |
| `timestamp` | `DATAHORA` | Persistido. |
| `speed` | `VELATU` | Persistido. |
| `altitude` | `ALTITUDE` | Persistido. |
| `heading` | `ORIENT` | Persistido após arredondamento para string inteira. |
| `device_id` | usado para resolver `FK_VEICOD` | Não fica no registro de localização; vínculo ocorre por veículo. |
| `protocol` | — | Descartado. |
| `gps_status` | — | Descartado. |
| `ignition` | — | Descartado. |
| `battery_voltage` | — | Descartado. |
| `panic` | — | Descartado. |

No modo de arquivo local, somente `device_id`, `protocol`, `timestamp`, latitude, longitude e velocidade são gravados. Heading, ignição, bateria, GPS e altitude são perdidos nesse modo.

## 6. O que chega ao motor comportamental

| Campo | Chega? | Problema |
|---|---:|---|
| latitude/longitude | Sim | Sem validação explícita de faixa/qualidade. |
| velocidade | Sim | Ausência vira zero. |
| heading | Sim | Ausência vira zero. |
| timestamp do equipamento | **Não corretamente** | O parser retorna string ISO; `db_handler` aceita apenas `datetime` e substitui string por `datetime.now()`. |
| ignição | Não | Impede reboque, ociosidade e ignição não autorizada. |
| tensão | Não | Impede bateria baixa/corte de alimentação. |
| status GPS | Não | Impede distinguir posição válida de perda de sinal. |
| protocolo | Não | Impede aplicar capacidades específicas por dispositivo. |
| pânico/alarme | Não | Sempre `False` e descartado. |
| altitude | Não | Persistida, mas não analisada. |

Consequência: T1.1 passou a calcular eventos usando tempo real, porém o fluxo de produção ainda injeta o horário de recebimento em vez do timestamp informado pelo equipamento. Isso deve ser corrigido antes de calibrar os detectores.

## 7. Capacidade para monitoramento patrimonial

| Função | Dados já recebidos | Prontidão real |
|---|---|---|
| Cerca eletrônica | latitude, longitude, timestamp | Parcial: falta normalização, estado e detector. |
| Desvio de rota | latitude, longitude, heading | Parcial: heading do simulador é aleatório. |
| Movimento armado | posição e velocidade | Parcial: falta estado armado e tolerância. |
| Reboque | movimento + ignição | Bloqueado no pipeline: ignição é descartada. |
| Ignição não autorizada | ignição | Bloqueado no pipeline. |
| Bateria baixa | tensão | Bloqueado no pipeline. |
| Alimentação removida | série temporal de tensão/alarme | Bloqueado no pipeline e sem alarme nativo. |
| Tracker offline | horário de recebimento | Implementável; falta SLA/estado. |
| GPS inválido | `gps_status` | Bloqueado no pipeline; parte dos protocolos usa valor fixo. |
| Pânico | nenhum valor real | Não implementável sem mapear mensagens/protocolo. |
| Tamper | nenhum valor real | Não implementável sem mapear mensagens/protocolo. |
| Evento nativo de towing | mensagens não reconhecidas | Não implementável no parser atual. |

## 8. Lacunas por protocolo

### Maxtrack

1. Resolver identidade real do dispositivo.
2. Não permitir que vários equipamentos usem `MAXTRACK-ANON` em produção.
3. Mapear alarmes e mensagens adicionais conforme o protocolo/modelo efetivamente usado.
4. Criar fixtures reais anonimizadas antes de habilitar no simulador principal.

### Suntech

1. Validar tipo/modelo da mensagem em vez de aceitar qualquer prefixo `ST`.
2. Extrair status GPS real.
3. Mapear alimentação, bateria interna, pânico e eventos nativos disponíveis no modelo contratado.
4. Preservar campos celulares úteis para diagnóstico de conectividade.

### Queclink

1. Criar roteamento genérico para mensagens `+RESP:<tipo>`.
2. Preservar `GTRIC` como posição periódica.
3. Adicionar tipos de mensagem de ignição, alimentação, towing, SOS e tamper somente após obter fixtures/documentação do equipamento usado.
4. Extrair validade/qualidade GPS real.

## 9. Contrato mínimo para a Etapa 1

O adaptador Tracker deve produzir:

```json
{
  "source": "tracker",
  "source_record_id": "protocol:device:timestamp:sequence",
  "protocol": "suntech|queclink|maxtrack",
  "device_id": "string",
  "observed_at": "ISO-8601",
  "received_at": "ISO-8601",
  "latitude": 0.0,
  "longitude": 0.0,
  "speed_kmh": 0.0,
  "heading_deg": 0.0,
  "altitude_m": null,
  "gps_valid": null,
  "ignition": null,
  "external_voltage": null,
  "panic": null,
  "alarm_type": null,
  "attributes": {}
}
```

Regras:

- `observed_at` vem do equipamento;
- `received_at` vem do servidor;
- campos não disponíveis são `null`, nunca zero/`False` inventado;
- latitude e longitude inválidas bloqueiam a observação;
- protocolo e mensagem original devem ser rastreáveis sem registrar segredos;
- identidade anônima não pode consolidar múltiplos equipamentos em produção;
- eventos nativos devem ser mapeados por lista explícita.

## 10. Validação automatizada

A tarefa adiciona testes no pacote ativo para:

- Maxtrack com identidade explícita;
- Suntech no formato emitido pelo simulador ativo;
- Queclink `GTRIC` no formato emitido pelo simulador ativo;
- rejeição de pacote desconhecido.

Os testes da raiz não devem ser executados junto aos testes de `aitrackdatadrivr`, pois a raiz contém outro pacote `server` legado com o mesmo nome. A suíte do código ativo deve ser executada a partir de `aitrackdatadrivr/`.

## 11. Critério de conclusão da P0.2

- Três parsers ativos inventariados.
- Campos extraídos, persistidos e descartados identificados.
- Limitações para cerca, rota, reboque, bateria e pânico registradas.
- Contrato mínimo da futura ingestão Tracker definido.
- Nenhuma alteração em parser de produção ou banco realizada nesta tarefa.

