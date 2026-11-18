# Validação — UI-5.1: configuração versionada dos agentes

**Executada em:** 18/11/2026 03:16 (`America/Sao_Paulo`)  
**Etapa:** 24 de 74  
**Checkpoint anterior:** `5323b2c`  
**Commit de implementação:** `f652e5d`

## Resultado esperado

Persistir objetivo, instruções, modelo, política, limites, estado e versão imutável
de cada agente, sem ativar inteligência fictícia.

## Resultado obtido

- Os cinco monitores existentes foram registrados como identidades estáveis
  `monitor-1` a `monitor-5`; não foram criados agentes ou prompts fictícios.
- Cada versão guarda objetivo, instruções, provedor, modelo, política de decisão,
  limites, autoria, motivo, timestamps e SHA-256 do conteúdo canônico.
- Novas versões começam em `draft`. A ativação exclusiva supersede a anterior e
  preserva snapshot, ator, motivo e correlação na auditoria.
- Triggers no MariaDB impedem alteração dos campos de conteúdo e exclusão de uma
  versão. Somente o ciclo `draft/active/superseded/retired` pode evoluir.
- `provider_code` e `model_code` são configuráveis. Nenhum SDK ou modelo específico
  foi acoplado nesta etapa.
- A API expõe listagem versionada, criação de draft e ativação auditada em
  `/api/agent-configurations`.

## Evidências

- Migration `032_create_versioned_agent_config.sql` aplicada; segunda execução:
  **0 migrations pendentes**.
- Prova transacional no MariaDB inseriu a versão sintética `999999`, bloqueou
  mudança de objetivo e exclusão com SQLSTATE `45000`, permitiu ativação e manteve
  objetivo/hash intactos.
- Rollback da prova confirmou **zero versões sintéticas residuais**.
- Runtime reiniciado: endpoint respondeu
  `agent-configurations.v1`, `count=0`; banco confirmou 5 identidades, 0 versões e
  0 configurações ativas.
- **11 testes específicos** cobriram schema, hash canônico, limites e API.
- Regressão backend: **344 aprovados e 12 integrações opt-in puladas**.
- Aviso de relógio UTC do simulador detectado durante o reinício foi corrigido no
  commit `fac8674`; 20 testes de simulador/parser continuaram aprovados.

## Limitações e segurança

- Nenhuma configuração foi ativada e nenhum modelo de linguagem é chamado ainda.
  A interface não deve afirmar que esses agentes já raciocinam autonomamente.
- A etapa 5.2 persistirá execuções; 5.3 definirá saída estruturada; 5.4 implementará
  o adaptador de provedor/modelo.
- Credenciais de provedor não pertencem às versões e não são armazenadas nessas
  tabelas; deverão vir de secret manager/ambiente autorizado.
- Autenticação administrativa da API e isolamento por organização permanecem nas
  etapas transversais de produção.

## Conclusão

**Aprovada.** Existe agora uma base versionada e imutável para definir a inteligência
de cada agente, sem simular execução nem escolher silenciosamente um modelo externo.
