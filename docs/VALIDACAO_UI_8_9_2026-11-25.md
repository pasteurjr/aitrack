# Validação UI-8.9 — acessibilidade

**Data:** 25/11/2026 11:10 (`America/Sao_Paulo`)

**Checkpoint:** `6baa35d` · **Implementação:** pendente de commit

## Resultado esperado

Fluxos de autenticação, cerca, incidentes e monitoramento devem ter rótulos, foco visível,
uso por teclado e alternativa para desenho no mapa.

## Resultado obtido

- círculo e polígono podem ser construídos por coordenadas sem clique/arraste no mapa;
- latitude/longitude e raio têm limites e mensagem de erro acessível;
- ao abrir o editor o foco entra nele; ao fechar, retorna ao botão de origem;
- avisos de validação usam `alert` e mensagens de estado usam regiões vivas;
- `jest-axe` foi aplicado às telas de cerca e saúde;
- Playwright Chromium abriu o build de produção isolado, confirmou heading, labels de
  e-mail/senha, dois primeiros passos de Tab e ausência de erro JavaScript; screenshot em
  `/tmp/aitrack-accessibility-login.png`.

## Evidências

- 15 testes focados (cerca e saúde) aprovados, incluindo 2 verificações axe;
- 22 suites frontend / **97 testes** aprovados;
- TypeScript e build de produção aprovados;
- **569 backend**, 12 testes de integração MySQL ignorados por dependerem de ambiente.

## Limitações

O servidor de desenvolvimento preexistente em `localhost:3000` carregava bundle antigo
com erro `Cannot find module 'crypto'`; a inspeção foi refeita no build atual em servidor
isolado. Playwright não percorreu mapa autenticado porque não havia credencial de teste
disponível. JSDOM/Axe não substitui medição visual de contraste em todas as telas nem
avaliação humana com NVDA/Firefox ou VoiceOver/Safari; portanto conformidade WCAG 2.2 AA
completa permanece pendente de homologação assistiva.
