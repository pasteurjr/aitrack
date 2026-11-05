# P0.3 — Validação do schema Dirija Bem em modo somente leitura

**Data:** 05/11/2026  
**Baseline:** `01e10a8`  
**Banco validado:** `dirijabem`  
**Servidor:** MariaDB 10.3.39  
**Método:** transação `READ ONLY`, consultas `SELECT`, `SHOW` e `EXPLAIN`, seguida de `ROLLBACK`

## 1. Resultado

O banco Dirija Bem contém os dados necessários para alimentar continuamente o pipeline unificado de monitoramento:

- identidade de usuário/motorista;
- cadastro de veículo;
- viagens com score e métricas comportamentais;
- pontos GPS com velocidade, aceleração e variação de direção;
- chave incremental adequada para polling por watermark.

Nenhum registro foi inserido, atualizado ou removido durante a validação.

## 2. Volume observado

| Indicador | Valor observado |
|---|---:|
| Viagens | 93.776 |
| Maior `CODVIA` | 946.366 |
| Maior `LOCDADCOD` | 69.347.742 |
| Data mais recente observada | 03/11/2026 |

A documentação anterior que mencionava aproximadamente 5.682 viagens está desatualizada e não deve ser usada para dimensionamento.

O último dado observado estava cerca de dois dias atrás em relação à auditoria. Isso não indica, sozinho, falha do banco; indica que o health check futuro deve medir lag e informar se simulador/aplicativo deixou de produzir dados.

## 3. Tabelas centrais confirmadas

### 3.1 `usuario`

Chave primária:

- `CODUSU` — inteiro, auto incremento.

Campos úteis ao monitoramento:

- `CODUSU`;
- `NOMUSU`;
- `USUTEL`;
- `USUEMAIL`;
- `PLACADEFAULT`.

Campos sensíveis que não devem entrar na ingestão de telemetria:

- senha/credencial;
- CPF;
- data de nascimento;
- sexo;
- endereço e CEP.

Contato telefônico/e-mail só poderá ser lido pelo módulo de comunicação com finalidade, autorização e controle de acesso definidos. O pipeline de posições usará apenas `CODUSU` como identidade.

Índices confirmados:

- chave primária em `CODUSU`;
- unicidade de CPF;
- unicidade de e-mail.

### 3.2 `veiculo`

Campos confirmados:

| Campo | Tipo | Uso |
|---|---|---|
| `PLACA` | `varchar(7)` | Chave primária e identidade do veículo. |
| `CODUSU` | `int` | Proprietário/usuário associado. |
| `CODMOD` | `int` | Modelo do veículo. |
| `ANO` | `int` | Ano. |
| `SEGURO` | `varchar(1)` | Indicador cadastral. |
| `VIN` | `varchar(17)` | Identidade veicular sensível. |

Relacionamentos confirmados:

- `CODUSU → usuario.CODUSU`;
- `CODMOD → modelo.CODMOD`.

O VIN não deve ser copiado para eventos ou prompts de IA sem necessidade explícita.

### 3.3 `viagem`

Identidade e período:

| Campo | Restrição |
|---|---|
| `CODVIA` | PK, auto incremento, não nulo. |
| `CODUSU` | Não nulo, indexado, FK para `usuario`. |
| `PLACA` | Não nulo e indexado. |
| `DATAHORINI` | Não nulo. |
| `DATAHORFIN` | Não nulo. |

Exposição e resultado:

- `DISTANCIA`;
- `DURACAO`;
- `SCORE`.

Métricas de velocidade:

- `OST` — proporção/tempo em excesso;
- `OSA` — excesso médio;
- `OSP` — pico de excesso.

Métricas de aceleração:

- `SAM`, `SAA`;
- `GAM`, `GAA`;
- `GAP`, `GAN`.

Métricas de direção:

- `BRP`;
- `BRM`;
- `BRA`.

Índices confirmados:

- chave primária em `CODVIA`;
- índice em `CODUSU`;
- índice em `PLACA`.

Relacionamentos efetivamente declarados:

- `CODUSU → usuario.CODUSU`.

Não foi encontrada foreign key declarada entre `viagem.PLACA` e `veiculo.PLACA`. A aplicação deve tolerar viagem cuja placa não encontre cadastro, registrar erro de identidade e não descartar a viagem.

### 3.4 `localizacaodados`

| Campo | Tipo | Restrição/uso |
|---|---|---|
| `LOCDADCOD` | `int` | PK, auto incremento, watermark. |
| `CODVIA` | `int` | Não nulo, índice e FK para `viagem`. |
| `DATAHORA` | `datetime` | Não nulo, horário observado. |
| `VELATU` | `float` | Velocidade. |
| `ACELLINATU` | `float` | Aceleração linear. |
| `ACELGPSATU` | `float` | Aceleração derivada do GPS. |
| `VARDIRATU` | `float` | Variação de direção. |
| `coords` | `point` | Longitude/latitude. |

Relacionamento confirmado:

- `CODVIA → viagem.CODVIA`, com cascata segundo o schema existente.

Índices confirmados:

- chave primária em `LOCDADCOD`;
- índice em `CODVIA`.

Não existe índice em `DATAHORA`. O leitor incremental não deverá consultar repetidamente por intervalo de data.

## 4. Estratégia incremental validada

Consulta-base:

```sql
SELECT
    LOCDADCOD,
    CODVIA,
    DATAHORA,
    VELATU,
    ACELLINATU,
    ACELGPSATU,
    VARDIRATU,
    coords
FROM localizacaodados
WHERE LOCDADCOD > ?
ORDER BY LOCDADCOD
LIMIT ?;
```

O `EXPLAIN` confirmou acesso `range` usando a chave primária. Em um watermark próximo do final da tabela, o banco restringiu a estimativa ao trecho final em vez de varrer por `DATAHORA`.

Regras para o consumidor:

1. Guardar watermark por fonte/consumidor no banco Tracker.
2. Ler lotes pequenos, inicialmente 500–1.000 pontos.
3. Processar em ordem crescente.
4. Confirmar o novo watermark somente após persistir/processar o lote.
5. Usar `source_record_id = dirijabem:LOCDADCOD` para idempotência.
6. Nunca atualizar `localizacaodados` para marcar processamento.
7. Aplicar backoff quando não houver registros novos.
8. Medir diferença entre último `DATAHORA`, horário atual e último watermark.

## 5. Ingestão de viagens concluídas

Consulta incremental por `CODVIA` também pode usar a chave primária:

```sql
SELECT
    CODVIA, CODUSU, PLACA,
    DATAHORINI, DATAHORFIN,
    DISTANCIA, DURACAO, SCORE,
    OST, OSA, OSP,
    SAM, SAA, GAM, GAA, GAP, GAN,
    BRP, BRM, BRA
FROM viagem
WHERE CODVIA > ?
ORDER BY CODVIA
LIMIT ?;
```

Como `DATAHORFIN` é não nulo no schema atual, as linhas representam viagens com período preenchido. Ainda assim, o consumidor deverá validar se fim é igual/posterior ao início e se os valores estão completos antes de produzir análise.

## 6. Qualidade de dados amostrada

### Últimos 10.000 pontos por chave

| Verificação | Resultado |
|---|---:|
| `coords` nulo | 0 |
| `VELATU` nulo | 0 |
| `ACELLINATU` nulo | 0 |
| `VARDIRATU` nulo | 0 |

### Últimas 1.000 viagens por chave

| Verificação | Resultado |
|---|---:|
| `SCORE` nulo | 5 |
| grupo OST/OSA/OSP incompleto | 5 |
| grupo de aceleração incompleto | 5 |
| grupo BRP/BRM/BRA incompleto | 5 |

Conclusão: o pipeline precisa aceitar métricas nulas e não pode transformar ausência em zero. Zero significa “medido sem ocorrência”; `null` significa “não calculado/indisponível”.

## 7. Conversão para a observação unificada

| Dirija Bem | Campo normalizado |
|---|---|
| `LOCDADCOD` | `source_record_id` |
| `CODVIA` | `trip_id` |
| `viagem.CODUSU` | `driver_id` e resolução do veículo |
| `viagem.PLACA` | resolução do veículo |
| `DATAHORA` | `observed_at` |
| `ST_Y(coords)` | `latitude` |
| `ST_X(coords)` | `longitude` |
| `VELATU` | `speed_kmh` |
| `ACELLINATU` | `acceleration_ms2` candidato |
| `ACELGPSATU` | aceleração GPS auxiliar |
| `VARDIRATU` | `heading_change_deg`/atributo comportamental |

O significado e unidade exatos de `ACELLINATU`, `ACELGPSATU` e `VARDIRATU` deverão ser preservados no contrato de origem até a calibração. O nome do campo não é evidência suficiente para converter unidade automaticamente.

## 8. Resolução de identidade

Ordem recomendada:

1. Resolver `CODVIA` na tabela `viagem`.
2. Obter `CODUSU` e `PLACA` da viagem.
3. Buscar `veiculo_unificado.codusu = CODUSU` e/ou placa normalizada.
4. Se houver Tracker vinculado, associar ao mesmo `vehicle_id`.
5. Se `CODUSU` e placa apontarem para veículos diferentes, criar evento de conflito e não fundir automaticamente.
6. Se não houver vínculo, enviar para fila de identidade pendente, mantendo o watermark e o dado bruto referenciado.

## 9. Segurança e privacidade

- Consumidor Dirija Bem operará somente leitura.
- Credenciais não serão incluídas em documentação, logs ou commits.
- Senha, CPF, endereço e data de nascimento não serão consultados pelo pipeline.
- Logs utilizarão IDs técnicos, nunca informações pessoais completas.
- Contatos para comunicação serão acessados por serviço autorizado separado.
- Prompts de IA receberão somente dados necessários ao incidente.
- Coordenadas e histórico são dados sensíveis e exigem controle de acesso/auditoria.

## 10. Riscos e decisões

| Item | Decisão |
|---|---|
| Tabela grande | Polling por PK/watermark, nunca por varredura temporal. |
| Métricas nulas | Preservar `null`; não converter para zero. |
| Placa sem FK | Validar identidade na aplicação. |
| Duas fontes para o mesmo veículo | Consolidar por `veiculo_unificado`. |
| Dado atrasado | Ordenar por chave de ingestão e preservar `observed_at`. |
| Ausência de dados recentes | Health/lag por fonte, sem declarar furto isoladamente. |
| PII na tabela de usuário | Minimização e serviço de contato separado. |

## 11. Critério de conclusão da P0.3

- Schema real das quatro tabelas centrais validado.
- Chaves, índices e relacionamentos confirmados.
- Campos comportamentais da viagem confirmados.
- Estratégia incremental por `LOCDADCOD` validada com `EXPLAIN`.
- Qualidade recente amostrada sem escrita.
- Restrições de privacidade documentadas.
- Nenhuma alteração realizada no banco Dirija Bem.

