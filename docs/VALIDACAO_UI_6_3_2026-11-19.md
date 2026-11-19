# Validação — UI-6.3: notificação interna

**Executada em:** 19/11/2026 16:09 (`America/Sao_Paulo`)  
**Etapa:** 41 de 74  
**Checkpoint anterior:** `179bb00`  
**Commit de implementação:** `ecf6ea7`

## Resultado esperado

Entregar a primeira ação persistente na interface, vinculada ao incidente e sem
qualquer canal externo.

## Resultado obtido

- Criação transacional gera ação `internal_notification`, percorre claim/sent/
  delivered e cria uma projeção de caixa de entrada.
- Notificação guarda destinatário operacional, incidente, título, corpo,
  prioridade, versão e leitura idempotente.
- Aba **Notificações** consulta somente o banco; abrir marca como lida e navega
  para o incidente vinculado.
- Identidade e leitura concluída são imutáveis; exclusão é bloqueada.

## Evidências

- Migration 044 aplicada/idempotente.
- Prova real entregou notificação `high` não lida; a ação terminou
  `delivered`, versão 4, uma tentativa e quatro eventos; replay não duplicou.
- Rollback confirmou zero resíduo e nenhum canal externo foi chamado.
- API real respondeu caixa vazia versionada.
- **431 testes backend**, **85 frontend**, TypeScript e build aprovados.
- Chrome 1440×900 exibiu a caixa real vazia sem overflow ou erro.

## Limitações

- A caixa real está vazia porque nenhuma configuração de agente está ativa.
- Atualização é por consulta da tela; push/WebSocket não faz parte desta etapa.

## Conclusão

**Aprovada.** A primeira ação operacional chega à UI com recibo, leitura e
vínculo de incidente, inteiramente dentro do sistema.
