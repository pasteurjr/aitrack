# Validação — UI-5.6: ferramentas somente leitura

**Executada em:** 18/11/2026 03:40 (`America/Sao_Paulo`)  
**Etapa:** 29 de 74  
**Checkpoint anterior:** `7f0c3af`  
**Commit de implementação:** `b55d328`

## Resultado esperado

Permitir que o agente consulte veículo, posição, histórico e cerca com escopo,
limite, retorno estruturado e auditoria, sem ferramenta arbitrária de escrita.

## Resultado obtido

- Registry contém somente `vehicle.get`, `position.latest`, `position.history` e
  `geofence.list_for_vehicle`.
- Não existe SQL genérico, HTTP/URL, criação, atualização, mensagem ou comando.
- `ToolScope` exige IDs canônicos, fontes Tracker/Dirija Bem e teto de 1–500 pontos.
- Veículo fora do escopo, fonte desconhecida, limite excessivo, argumento extra e
  ferramenta não registrada são negados antes da consulta.
- Posições unem as fontes permitidas, são ordenadas e truncadas no limite; identidade
  e cercas usam o banco operacional comum.
- Resultado usa `agent-tool-result.v1`. Recibo guarda ferramenta, argumentos/escopo,
  hashes, resumo, status, latência, erro e correlação; não guarda credencial.
- Sucesso, negação e falha de repositório são auditados separadamente.

## Evidências

- Migration `035_create_agent_tool_audit.sql` aplicada; runner repetido informou
  **0 migrations pendentes**.
- Prova real no veículo canônico 9 retornou identidade, última posição Tracker,
  cinco pontos de histórico e uma cerca atribuída.
- Quatro ferramentas geraram quatro recibos `succeeded`; tentativa de `sql.query`
  gerou um recibo `denied` sem atingir o repositório.
- Limpeza confirmou **zero recibos sintéticos residuais**.
- A primeira consulta histórica expôs plano lento (>30 s). Troca para chaves
  monotônicas e seleção das 20 viagens recentes reduziu leitura combinada para
  aproximadamente 0,2 s, mantendo limite final.
- **12 testes específicos** e **392 testes backend** aprovados; 12 integrações opt-in
  puladas.

## Limitações e segurança

- A ferramenta de cercas cobre atribuição direta a veículo; expansão para grupos e
  motorista deve manter o mesmo escopo canônico.
- Eventos, incidentes e dados do proprietário ainda não foram expostos como tools.
- Esta etapa define ferramentas globais seguras. A UI-5.7 determinará qual versão de
  agente pode chamar cada uma e com quais parâmetros.
- Auditoria escreve apenas no schema operacional; as fontes Tracker/Dirija Bem são
  consultadas em leitura.

## Conclusão

**Aprovada.** O agente pode obter contexto real e limitado sem receber acesso
arbitrário ao banco, à rede ou a operações externas.
