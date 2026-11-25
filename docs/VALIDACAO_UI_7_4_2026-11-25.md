# Validação UI-7.4 — replay de viagem

**Data:** 25/11/2026 00:49 (`America/Sao_Paulo`)

**Checkpoint anterior:** `0341969` (00:44:21 -03)

**Implementação:** `d3db04d`

## Resultado esperado

Permitir que o operador reproduza rota, posições, episódios e transições na ordem
temporal, com velocidade controlável, sem misturar replay e operação ao vivo e sem
gerar qualquer escrita, incidente ou ação externa.

## Resultado obtido

- endpoint limitado a 5.000 posições e indexado por execução/horário;
- contrato `trip-replay.v1` retorna `mode=replay` e `read_only=true`;
- rota planejada preserva versão e corredor; posições realizadas preservam fonte;
- timeline única usa timestamp, prioridade de tipo e ID estável como desempate;
- tela dedicada exibe aviso de replay, rota planejada/realizada e eventos;
- controles de reproduzir/pausar, reiniciar, seek e 0,5×/1×/2×/4×;
- velocidade muda apenas o relógio visual, nunca timestamps ou dados do detector;
- consulta não chama detector, correlacionador de incidentes ou fila de ações.

## Evidências

- migration 057 aplicada; segunda execução: **0 pendentes**;
- testes focados backend: **10 passed**;
- regressão backend: **506 passed, 12 skipped**;
- frontend: **86 testes**, TypeScript e build de produção aprovados;
- prova MariaDB em transação: 3 posições, uma mudança de execução e um episódio
  resultaram em 6 eventos na ordem esperada;
- duas consultas retornaram conteúdo idêntico e as contagens antes/depois ficaram
  iguais (`3/1/1`); rollback deixou **0 resíduos**.

## Limitações

- Recibos anteriores à migration 057 não continham latitude/longitude e, por
  segurança, são omitidos em vez de receber coordenadas fabricadas.
- A seleção inicial exige o UUID da execução. Descoberta/listagem amigável pode
  ser incorporada ao fluxo visual de gestão de rotas.
