# Validação UI-8.7 — carga e recuperação

**Data:** 25/11/2026 10:57 (`America/Sao_Paulo`)

**Checkpoint:** `61fbbd9` · **Implementação:** `8f7d4f6`

## Resultado esperado

Replays e restart não podem perder nem duplicar telemetria aceita, incidente ou ação;
leases vencidos precisam ser recuperados. Carga não pode atingir o banco compartilhado.

## Resultado obtido

O harness usa SQLite temporário em WAL, transações reais e oito workers. Persistiu 5.000
correlações, repetiu o lote inteiro, fechou/reabriu a persistência e recuperou 100 leases.
Alvos diferentes de `localhost`, `127.0.0.1` e `::1` são recusados antes do ensaio.

## Medições

- throughput: **856,61/s**;
- persistência: **p95 1,49 ms**, **p99 2,75 ms**;
- replay: **p95 0,013 ms**;
- duplicidade: **0** em receipts, incidentes e ações;
- RPO: **0 registros**; RTO: **0,0084 s**;
- leases vencidos recuperados: **100/100**;
- regressão: **566 aprovados, 12 ignorados**.

Evidência bruta: `docs/evidence/UI_8_7_SAFE_LOAD_2026-11-25.json`.

## Limitação e gate

Este é um baseline de correção e recuperação, não uma certificação de capacidade do
MySQL/Tomcat em `192.168.0.100`, nem de IA/mensagem/voz. Carga real exige homologação
isolada, dados sintéticos, canais sandbox e autorização operacional expressa.
