# Validação UI-8.2 — papéis e permissões

**Data:** 25/11/2026 10:33 (`America/Sao_Paulo`)

**Checkpoint:** `707a59c` · **Implementação:** `6d34341`

## Resultado

O RBAC possui 22 permissões e sete papéis: visualizador, operador, supervisor,
configurador, auditor, administrador da empresa e administrador da plataforma.
Papéis são atribuídos ao vínculo usuário–tenant. A matriz método/rota separa leitura,
operação, classificação, configuração, aprovação, exportação, agenda e comandos.
Rota mutável desconhecida exige `platform.admin` em vez de ser liberada por omissão.

## Evidências

- migration 063 aplicada/idempotente;
- 18 testes focados e matriz parametrizada de rotas;
- prova MariaDB: 22 permissões, 7 papéis, viewer negado em `incident.operate` e
  operator autorizado; rollback deixou zero tenant;
- regressão: 546 backend e 88 frontend, TypeScript e build aprovados;
- navegação oculta áreas sem capacidade, mantendo o backend como autoridade.

## Limitação

Alguns contratos antigos ainda carregam `actor_id` no corpo. Eles não concedem
permissão, mas serão substituídos pelo principal autenticado na auditoria transversal.
