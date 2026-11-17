# Validação — UI-4.2: modelo de sensor e leitura

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 13 de 74  
**Checkpoint anterior:** `9e559c4`

## Resultado esperado

Persistir cada leitura com sensor, valor tipado, unidade, qualidade, origem,
horário informado pela fonte, horário de recebimento e correlação idempotente,
sem confundir capacidade física com leitura operacional.

## Resultado obtido

- `monitoramento.sensors` representa a instância observada por fonte, protocolo,
  dispositivo e capacidade, com vínculo opcional à identidade operacional comum.
- `monitoramento.sensor_readings` mantém leitura imutável em JSON válido, tipo,
  unidade, qualidade, dois horários, correlação e referência ao registro de origem.
- A chave `(sensor_id, correlation_id)` torna o reprocessamento idempotente.
- A ingestão Tracker normaliza somente capacidades `confirmed` no catálogo ativo:
  posição, velocidade, direção, ignição, tensão externa e sinais específicos que o
  protocolo comprova.
- `panic=False` fixado pelo parser não é gravado como leitura real.
- Se a identidade operacional ainda não existir, a origem externa é preservada e o
  sensor poderá ser reconciliado posteriormente, sem perda de telemetria.
- A posição Tracker é confirmada antes da trilha de sensores. Falha no novo modelo
  sofre rollback isolado e não interrompe rastreamento, motor comportamental ou
  cercas.

## Evidências

- Migration `024_create_sensor_readings.sql` aplicada; segunda execução em dry-run:
  **0 migrations pendentes**.
- Prova transacional no MariaDB real inseriu **6 leituras** Maxtrack com qualidade
  `valid`, horários distintos e capacidades exatas; o rollback deixou **0 resíduos**.
- Testes específicos de sensores, catálogo e runner: **16 aprovados**.
- Suíte backend completa: **255 aprovados e 12 integrações opt-in puladas**.
- Compilação Python e `git diff --check`: aprovados.

## Limitações e decisões

- O adaptador de ingestão implementado nesta etapa é o Tracker, pois seus três
  parsers já entregam sinais físicos. O schema e a chave de origem aceitam Dirija
  Bem, mas nenhum sensor físico é inventado a partir dos eventos comportamentais.
- O backend já em execução precisa de reinício controlado para carregar a nova
  persistência; leituras anteriores não são retroativamente fabricadas.
- Saúde, leitura desatualizada e política de detector pertencem às etapas UI-4.3 a
  UI-4.5. `quality=valid` significa que o parser aceitou o valor, não que uma regra
  operacional avaliou a saúde do sensor.
- O relógio recebido é ajustado ao observado quando o equipamento informa instante
  futuro, preservando a restrição `received_at >= observed_at`; a futura política de
  qualidade poderá classificar esse desvio explicitamente.

## Conclusão

**Aprovada.** O sistema agora possui trilha persistente, tipada e idempotente para
leituras reais/simuladas que atravessam o mesmo pipeline Tracker, sem dados mockados
e sem converter ausência de suporte em leitura falsa.
