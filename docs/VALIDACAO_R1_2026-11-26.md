# Validação R1 — vulnerabilidades dos frontends

**Data:** 26/11/2026 00:10 (`America/Sao_Paulo`)  
**Checkpoint pré-etapa:** `7c14fbc`  
**Resultado:** **concluída para os dois frontends**

## Resultado esperado

Eliminar as vulnerabilidades críticas e altas auditadas nos dois aplicativos, sem quebrar
fluxos, autenticação, configurações de API, testes ou builds de produção.

## Alterações

- removido `react-scripts@5.0.1` dos dois frontends;
- migrados servidor e build para Vite 7.3.8 e testes para Vitest 4.1.12;
- adotados `VITE_API_BASE_URL` e `VITE_MAP_TILE_URL`, preservando compatibilidade explícita
  com as antigas `REACT_APP_API_BASE_URL` e `REACT_APP_MAP_TILE_URL`;
- migrados mocks Jest para Vitest no App 2 e atualizados os testes de componentes;
- excluídos template e tipos CRA; ambos os servidores locais mantêm as portas 3001 e 3003;
- CRA está depreciado pelo React desde 14/02/2025; a documentação oficial recomenda migrar
  aplicações existentes para um framework ou ferramenta de build mantida. Fonte:
  [Sunsetting Create React App — React](https://react.dev/blog/2025/02/14/sunsetting-create-react-app).

A correção segura inicial no App 1 (`npm audit fix`, sem `--force`) baixou 3 críticas e 37
altas para zero críticas e 16 altas. A migração posterior retirou o restante da cadeia CRA.
No App 2, a cadeia CRA retinha as 16 altas mesmo após as correções compatíveis; a migração
removeu a árvore vulnerável. Nenhum `npm audit fix --force` foi usado.

## Evidências

| Verificação | App 1 | App 2 |
|---|---:|---:|
| `npm audit` antes | 3 críticas, 37 altas, 64 totais | 0 críticas, 16 altas, 29 totais |
| `npm audit` depois | **0 vulnerabilidades** | **0 vulnerabilidades** |
| Instalação limpa `npm ci` | aprovada; zero achados | aprovada; zero achados |
| Testes | 1 aprovado | 97 aprovados em 22 suítes |
| TypeScript | aprovado | aprovado |
| Build de produção | aprovado | aprovado, com aviso de um chunk acima de 500 kB |
| Preview HTTP | HTML + 2 assets com status 200 | HTML + 2 assets com status 200 |

Resultados detalhados e hashes SHA-256 dos lockfiles: `docs/evidence/UI_R1_FRONTEND_AUDIT_2026-11-26.json`.

## Limitações e risco restante

- o aviso do chunk do App 2 é de tamanho/performance, não falha de build nem achado de auditoria;
  planejar divisão do bundle em tarefa própria se medições de carregamento justificarem;
- `npm install` via npm 10.9.2 apresentou erro interno do Arborist ao compor a árvore nova;
  a instalação do lockfile com `npm ci` pelo mesmo npm passou nos dois apps. A alteração dos
  lockfiles foi feita com npm 11.6.4;
- `npm audit` cobre dependências instaladas; não comprova rotação de segredos no histórico,
  DAST autenticado ou TLS no ambiente-alvo. Esses gates continuam em R2/R3.

## Validação da conclusão

Builds com valores sintéticos antigos confirmaram a compatibilidade das variáveis legadas.
Os dois builds migrados foram servidos em previews locais isolados. O HTML e os bundles
referenciados responderam HTTP 200. Servidores de preview iniciados para esta checagem foram
encerrados pelos próprios identificadores de sessão. Não foi acessado banco nem enviado
tráfego a destinatários externos.
