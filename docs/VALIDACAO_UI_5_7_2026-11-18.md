# Validação — UI-5.7: política de ferramentas por agente

**Executada em:** 18/11/2026 03:43 (`America/Sao_Paulo`)  
**Etapa:** 30 de 74  
**Checkpoint anterior:** `b2a15f3`  
**Commit de implementação:** `dad1d43`

## Resultado esperado

Aplicar uma allowlist imutável por versão de configuração, bloqueando toda
ferramenta, fonte, argumento ou volume fora da função declarada do agente.

## Resultado obtido

- `agent_tool_policies` vincula permissão à versão exata da configuração.
- Cada permissão restringe ferramenta, argumentos, fontes e limite máximo.
- Ausência de política nega por padrão; não existe permissão global implícita.
- Políticas só podem ser adicionadas a configurações `draft` e tornam-se
  imutáveis no banco; alteração e exclusão são bloqueadas por triggers.
- O executor exige `config_version_id`, autoriza antes de consultar e grava no
  recibo a versão e a política efetivamente usadas.
- O limite omitido em histórico/cercas é avaliado pelo volume real do escopo,
  impedindo contornar a política pela omissão do parâmetro.

## Evidências

- Migration `036_create_agent_tool_policies.sql` aplicada; segunda execução
  informou **0 migrations pendentes**.
- Prova transacional MariaDB inseriu permissão para `position.history`, fonte
  Tracker e no máximo cinco pontos.
- A prova autorizou a consulta declarada e negou ferramenta ausente, seis pontos
  e fonte Dirija Bem.
- `UPDATE` e `DELETE` foram recusados com SQLSTATE `45000`.
- Rollback e consultas posteriores confirmaram **zero configurações e zero
  políticas sintéticas residuais**.
- **16 testes focados** e **396 testes backend** aprovados; 12 integrações
  opt-in puladas.

## Limitações e segurança

- Nenhuma configuração de agente está ativa; portanto a etapa não realizou
  chamada de modelo externo nem gerou custo.
- A allowlist atual cobre as quatro ferramentas somente leitura da UI-5.6.
- Criar uma nova versão é o único meio de alterar permissões; nível de
  autonomia e autorização de ações pertencem à UI-5.8.

## Conclusão

**Aprovada.** Cada versão de agente passa a operar com menor privilégio,
negação por padrão e trilha que identifica a permissão usada.
