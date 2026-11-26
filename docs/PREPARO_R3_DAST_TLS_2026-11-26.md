# Preparação R3 — escopo DAST e TLS

**Data:** 26/11/2026 00:52 (`America/Sao_Paulo`)

**Checkpoint pré-preparação:** `1b6e0ed`

**Estado:** matriz preparada; execução remota **não iniciada**

## Limite desta preparação

A inspeção foi feita estaticamente no código local. Não houve requisição HTTP, autenticação,
scan de portas, alteração de banco nem tentativa de exploração. O DAST real requer R2 concluída
(identidade de banco dedicada) e ambiente HTTPS isolado de homologação.

## Áreas e cobertura a executar em homologação

| Área | Rotas registradas | Verificações previstas | Segurança para scan ativo |
|---|---|---|---|
| Auth e sessão | `/api/auth/login`, `/me`, `/logout`, `/recover`, `/reset` | 401 sem sessão; login/logout; cookie HttpOnly/SameSite/Secure em HTTPS; CSRF em mutações; recuperação não enumera conta e não expõe token debug. | Usar usuários de teste e provedor de e-mail sandbox; não disparar reset para destinatário real. |
| Health | `/api/health/live`, `/ready`, `/integrations` | liveness/readiness; detalhe sem permissão negado; erros sem stack trace, token ou topologia sensível. | GET passivo; não forçar outage de fonte real. |
| RBAC e tenant | incidentes, cercas, agentes, relatórios/exports, rotas e auditoria | matriz de papéis; negação por menor privilégio; IDs conhecidos de outro tenant retornam ausência/negação sem dados; ator sempre vem da sessão. | Somente dois tenants sintéticos no banco isolado. |
| Incidentes e ações de monitoramento | `/api/incidents/*`, `/api/monitors/*`, `/api/agent-configurations/*`, `/api/agent-controls/*` | autorização, validação de payload, concorrência, idempotência, audit trail, redação de erro e ausência de ação externa. | Mutação somente em dataset descartável; canais de mensagem/voz em sandbox. |
| Cercas | `/api/geofences/*` | geometria/campos inválidos, ownership, atribuição, permissões, concorrência e não duplicidade de incidentes. | Banco isolado; não executar comandos físicos nem usar frota real. |
| Telemetria e frota | `/api/unified/*`, `/api/vehicles/*`, `/api/positions/*`, `/api/fleet/*` | autenticação, autorização, limite de paginação, injection, IDOR, validação de parâmetros e exposição de dados pessoais. | GET no ambiente de homologação com dados sintéticos; limitar volume e taxa. |

## Rotas fora do active fuzzing até isolamento específico

- `/api/dirijabem/user/<id>/start`, `/start-synthetic` e `/stop`: podem iniciar replay/simulação
  com persistência no banco Dirija Bem. Não enviar POST de scanner a essas rotas.
- `/api/vehicles/<id>/commands` e `/authorization`: podem persistir pedidos/decisões de comando.
  Testar primeiro autenticação/negação; permitir mutações apenas com authorizer físico desabilitado,
  veículo de laboratório e confirmação de zero saída para dispositivos.
- `/api/routes/*` e endpoints POST/PUT/DELETE de incidentes/cercas/agentes: testar em banco
  descartável; nunca apontar o scanner ao banco compartilhado.
- `/api/auth/recover` e integrações de mensagem/voz: sandbox sem destinatários reais.

## Checklist TLS para o hostname de homologação

1. DNS resolve para o alvo isolado aprovado; certificado vigente cobre o hostname e cadeia valida.
2. HTTPS não permite downgrade; TLS 1.2+ negociado; protocolos/cifras fracos rejeitados.
3. Redirecionamento HTTP → HTTPS e HSTS presentes no modo production; cookie de sessão `Secure`.
4. CORS aceita somente origens de homologação autorizadas; nenhum segredo aparece em headers,
   HTML, source maps, bundles ou respostas de erro.
5. Registrar ferramenta/versão, hostname mascarado se necessário, data, perfil e evidência
   sanitizada; anexar achados com severidade, rota, reprodução e correção.

## Bloqueios antes da execução

- R2 continua sem identidade dedicada: a credencial ativa é global/compartilhada e permanece no
  histórico Git. Não iniciar backend/DAST com ela em ambiente compartilhado.
- Não foi fornecido hostname HTTPS, certificado, janela de teste, tenant/usuário de teste,
  banco descartável nem sandbox de canais.
- Para liberar active scan, DBA/infra deve fornecer ambiente isolado, usuário least-privilege,
  contas sintéticas e configuração de sandbox; segurança/owner aprova janela e limites de carga.

## Resultado obtido

A matriz inclui auth, RBAC, isolamento tenant, incidentes, cercas, agentes, frota, operações
com efeitos e TLS. A análise local confirmou que existem endpoints mutativos de replay Dirija Bem
e comandos; eles foram explicitamente excluídos de fuzzing ativo até isolamento. **R3 continua
pendente e não há resultado de DAST/TLS para declarar.**
