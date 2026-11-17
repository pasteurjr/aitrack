# Validação — UI-0.3: fallback silencioso no detalhe do monitor

**Executada em:** 17/11/2026 11:05 (`America/Sao_Paulo`)  
**Etapa:** 6 de 74  
**Implementação original:** `0c2f596`  
**Objetivo:** provar que falhas da API não são apresentadas como score, contagem de eventos ou estado operacional válidos.

## Resultado esperado

- O endpoint de veículos do monitor deve devolver dados comportamentais calculados quando o motor estiver disponível.
- Uma falha no enriquecimento comportamental deve produzir erro explícito, sem o antigo fallback `score 85`, `0 eventos` e estado `ok`.
- O frontend deve limpar dados anteriores, apresentar estado de erro acessível e permitir nova tentativa.

## Resultado obtido

A implementação já estava incorporada à `main`, embora o plano consolidado ainda a marcasse como pendente. A revisão confirmou:

- `GET /api/monitors/<id>/vehicles` devolve `503` com código `BEHAVIORAL_DATA_UNAVAILABLE` quando o enriquecimento falha;
- a resposta de erro não contém score ou estado inventado;
- `MonitorDashboard` limpa monitor e veículos antes da nova consulta;
- falha de detalhe exibe `Informação indisponível` e informa que scores, eventos e estados não foram inventados;
- o operador pode usar `Tentar novamente` ou `Voltar`;
- no runtime real, o monitor 1 devolveu `SIM-1000` e `SIM-1001` com score `100.0`, estado `ok` e contagem diária `0`, provenientes do backend em execução.

## Evidências executadas

### Backend

```text
tests/test_monitor_api.py: 3 passed
suíte backend: 242 passed, 12 skipped
```

Os testes cobrem o caminho válido e a falha forçada do motor, verificando status HTTP, código de erro e ausência do valor `85`.

### Frontend

```text
MonitorDashboard + MonitorDetailView + AsyncDataState: 9 passed
suíte frontend completa: 65 passed
TypeScript: npx tsc --noEmit — aprovado
Build de produção: npm run build — aprovado
```

Os testes verificam erro acessível, ausência do score inventado e recuperação após nova tentativa.

### Runtime

```text
GET http://127.0.0.1:5009/api/monitors/1/vehicles — HTTP 200
SIM-1000: score_atual=100.0, status=ok, total_eventos_hoje=0
SIM-1001: score_atual=100.0, status=ok, total_eventos_hoje=0
```

## Limitações e observações

- O `.venv` descrito no `AGENTS.md` não existe nesta cópia de trabalho.
- O ambiente Conda `aitrack` existe, mas não possui `pytest` e usa Python 3.9.23.
- Para não instalar ou alterar dependências, a validação backend usou o Python base do Miniconda, que já contém as dependências do projeto. A correção do ambiente deve ser tratada separadamente; ela não altera o resultado funcional da UI-0.3.
- Os avisos de `baseline-browser-mapping` e `caniuse-lite` desatualizados não impediram testes, tipagem ou build e não foram tratados nesta etapa.

## Conclusão

**Aprovada.** O fallback silencioso não está presente no código atual e os caminhos de sucesso, erro e nova tentativa foram comprovados. A pendência era documental, não uma lacuna de implementação.
