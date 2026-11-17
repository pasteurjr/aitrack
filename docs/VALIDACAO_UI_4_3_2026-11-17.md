# Validação — UI-4.3: política versionada de detector

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 14 de 74  
**Checkpoint anterior:** `09cc24f`

## Resultado esperado

Separar a capacidade física do equipamento da regra operacional, mantendo versão,
escopo, limites/parâmetros e trilha de auditoria para cada detector.

## Resultado obtido

- `detector_policies` mantém chave lógica, versão imutável, tipo do detector,
  capacidade relacionada, escopo global/fonte/monitor/veículo e parâmetros JSON.
- A política nasce em `draft`; ativação transacional substitui a versão ativa do
  mesmo escopo e marca a anterior como `superseded`.
- A chave ativa única impede duas versões ativas para a mesma política e escopo.
- `detector_policy_audit` registra criação, ativação, substituição/retirada, ator,
  motivo, snapshot e correlação.
- API `detector-policies.v1` lista, cria e ativa versões, com erros estruturados para
  payload inválido, política ausente e falha de persistência.
- A validação exige ator, motivo, parâmetros não vazios e referência explícita em
  todo escopo que não seja global.

## Evidências

- Migration `025_create_detector_policies.sql` aplicada e reexecução dry-run:
  **0 migrations pendentes**.
- Prova transacional MariaDB criou política de veículo, ativou limites 11,5/12,2 V,
  gravou auditoria e confirmou versão/escopo; rollback deixou **0 resíduos**.
- Endpoint real em processo: HTTP 200, contrato `detector-policies.v1`, zero políticas
  (nenhuma regra foi ativada sem homologação).
- Testes específicos de política/runner: **10 aprovados**.
- Suíte backend completa: **260 aprovados e 12 integrações opt-in puladas**.
- Compilação Python e `git diff --check`: aprovados.

## Limitações e segurança

- Esta etapa cria o modelo e ciclo de versão; não escolhe limites de detecção nem
  ativa detector. Alimentação, bateria e offline serão definidos/testados nas
  etapas UI-4.8 e UI-4.9.
- O catálogo diz se o sinal existe; uma política ativa diz como interpretá-lo. Uma
  política nunca transforma capacidade `unknown/unavailable` em suporte físico.
- A aplicação ainda não possui autenticação transversal. A autoria é obrigatória e
  auditada, mas controle de acesso centralizado pertence ao bloco de produção; até
  lá, os endpoints mutáveis não devem ser expostos fora da rede controlada.
- A interface de gestão e a ativação amigável serão entregues nas etapas UI-4.4 a
  UI-4.6; esta etapa valida contrato e persistência.

## Conclusão

**Aprovada.** Capacidade, leitura e política agora são entidades distintas e
rastreáveis, permitindo evoluir detectores sem reescrever histórico ou anunciar
hardware inexistente.
