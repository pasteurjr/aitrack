# Validação UI-8.6 — métricas, logs e alertas técnicos

**Data:** 25/11/2026 10:53 (`America/Sao_Paulo`)

**Checkpoint:** `4e3d8be` · **Implementação:** `5776a5b`

## Resultado esperado

Erros, latência, indisponibilidade e recuperação precisam ser observáveis sem usar veículo,
usuário, request ID ou dado pessoal como label de métrica e sem vazar segredo em log.

## Resultado obtido

- requisições geram contador e buckets por método, rota normalizada e status;
- logs JSON contêm correlação, tenant/principal por identificador e duração, nunca corpo;
- formatter redige token, senha, Bearer, JSON sensível e credencial em URL;
- alertas técnicos persistem abertura, observação e recuperação com deduplicação;
- `/api/metrics` e detalhe técnico exigem `health.read`;
- nenhuma regra desta fase envia mensagem/chamada externa.

## Evidências

- migration 067 aplicada;
- ensaio transacional produziu `opened`, `observed`, `recovered`, manteve uma linha,
  incrementou duas observações, redigiu segredo e deixou `rollback_residue = 0`;
- **563 backend**, **93 frontend**, TypeScript e build aprovados.

## Limitação registrada

As métricas residem no processo Flask e reiniciam com ele. Em implantação multi-instância,
devem ser exportadas para um coletor central. O canal externo dos alertas técnicos exige
política e destinatário operacional explícitos; por segurança não foi inferido.
