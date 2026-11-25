# Validação UI-8.8 — segurança e privacidade

**Data:** 25/11/2026 11:04 (`America/Sao_Paulo`)

**Checkpoint:** `601e524` · **Implementação:** `be729da`

## Resultado esperado

Auditar credenciais, autenticação, isolamento, headers, dependências, dados pessoais,
retenção e subprocessadores. Zero crítico/alto aberto é condição para produção.

## Tratamentos executados

- código e utilitários não possuem fallback de host/usuário/senha; ambiente é obrigatório;
- valores conhecidos foram redigidos de documentos/sessões no working tree;
- scanner reproduzível cobre arquivos rastreados e novos sem imprimir o valor encontrado;
- cookie é Secure em produção; CSP, HSTS, anti-frame, nosniff e Permissions-Policy ativos;
- mensagens 5xx não devolvem exceção/credencial ao cliente;
- token de recuperação debug é proibido em produção;
- política versionada inventaria dados, finalidade, acesso e retenção proposta.

## Evidências automatizadas

- scanner local: **0 achados**;
- `pip-audit`: **0 vulnerabilidades em 11 dependências**;
- Bandit após correção: **0 alto**, 40 médios e 6 baixos;
- npm antes: 3 críticos, 37 altos, 64 totais;
- npm após correções compatíveis: **0 crítico**, 16 altos, 29 totais;
- regressão: **569 backend**, **93 frontend**, TypeScript e build aprovados.

Resumo bruto: `docs/evidence/UI_8_8_SECURITY_AUDIT_2026-11-25.json`.

## Decisão: NO-GO

Produção continua bloqueada por 16 achados altos transitivos da cadeia antiga
`react-scripts`, rotação não comprovada de credenciais presentes em commits históricos
(4 ocorrências de um valor conhecido e 2 do literal legado), e ausência de DAST autenticado
e validação TLS no ambiente-alvo. Não foi feito `npm audit fix --force`, pois a sugestão
instalaria `react-scripts@0.0.0` e quebraria o build sem uma migração planejada.
