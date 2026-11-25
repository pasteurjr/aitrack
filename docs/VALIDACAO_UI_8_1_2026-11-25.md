# Validação UI-8.1 — autenticação

**Data:** 25/11/2026 01:20 (`America/Sao_Paulo`)

**Checkpoint:** `0547c1a` · **Implementação:** `2e4f27a`

## Resultado

- sessão opaca aleatória; banco guarda somente SHA-256 do token e CSRF;
- senha BCrypt com salt/custo 12 e política mínima de 12 caracteres;
- cookie de sessão HttpOnly/SameSite e cookie CSRF legível pelo cliente;
- expiração ociosa de 30 minutos e absoluta de 8 horas;
- cinco falhas bloqueiam por 15 minutos; login inválido não enumera usuário;
- logout revoga; reset é único e revoga todas as sessões anteriores;
- API `/api/*` protegida por padrão, com allowlist para login/reset, live e callback HMAC;
- CORS restrito às origens configuradas e suporte a credenciais;
- App 1 e App 2 possuem login, restauração e logout;
- bootstrap exige e-mail/senha em variáveis; migration não cria credencial padrão.

## Evidências

- migration 062 aplicada e segunda execução sem pendências;
- prova MariaDB em transação validou login, CSRF, reset, revogação, uso único e
  eventos imutáveis; rollback deixou zero usuário e zero tenant;
- `/api/health/live` anônimo = 200; `/api/incidents` anônimo = 401;
- 533 testes backend, 88 App 2 e 1 App 1 aprovados;
- TypeScript e builds de produção dos dois frontends aprovados.

## Limitações

O envio do token de recuperação depende de canal configurado; retorno do token só
existe em modo debug explícito. Implantação HTTPS deve definir
`AITRACK_COOKIE_SECURE=true`.
