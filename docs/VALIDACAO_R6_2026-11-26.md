# Validação R6 — acessibilidade automatizável

**Data:** 26/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 6 de 8 — R6  
**Checkpoint anterior:** `6fa38ee`  
**Commit de implementação:** `f44ff8d`  
**Escopo:** frontend App 2 (`aitrackdatadrivr/frontend`), execução local de teste. Nenhum banco ou credencial foi acessado.

## Objetivo e critério

Melhorar o acesso por teclado e tecnologias assistivas aos fluxos críticos, medir contrastes dos estados corrigidos e executar validações automatizadas. A aceitação completa de R6 também exige percorrer os fluxos internos autenticados com operador e leitor de tela; essa parte não foi simulada nem declarada concluída.

## Defeitos encontrados e correções

- A barra de menus não era landmark de navegação e o conteúdo principal não tinha landmark nem link de salto. O app agora usa `header`, `nav` com nome acessível, `main#main-content`, link “Pular para o conteúdo principal” e `aria-current="page"` na navegação ativa.
- As listas de veículo Tracker e motorista Dirija Bem não tinham nome acessível em `BehavioralDashboard` e `VehicleList`; foram nomeadas com `aria-label`.
- Estilos inline removiam o contorno de foco dessas listas. Removidos; foco global visível adicionado com `:focus-visible`.
- O erro de autenticação não era associado aos campos. E-mail e senha agora recebem `aria-invalid` e `aria-describedby` enquanto o alerta está presente.
- O botão “Entrar” tinha contraste insuficiente (3,76:1 antes). A navegação ativa também não atingia o critério de texto normal (2,54:1 antes). As cores foram escurecidas.
- `TripReplayPanel` e `HealthIntegrationsPanel` deixaram de criar landmarks `main` aninhados no landmark principal do app; agora são seções nomeadas.

## Resultado obtido e validação

- **Testes frontend:** 98 passaram em 22 arquivos (`npm test -- --reporter=dot`). Incluem teste de landmarks/link/estado da navegação, associação do erro de login e `jest-axe` no login em estado inicial e com erro. Os testes existentes axe para editor de cerca e saúde também passaram na suíte.
- **Build:** `npm run build` passou (`tsc --noEmit` e Vite). Permanece o aviso já existente de bundle JavaScript acima de 500 kB (574,03 kB); não impede o build.
- **Playwright Chromium headless:** abriu o build compilado em `http://127.0.0.1:4174` com respostas de autenticação interceptadas localmente. A sequência observada foi `auth-email` → `auth-password` → `Entrar`; tentativa inválida mostrou alerta ligado aos dois campos (`aria-describedby="auth-error"`, `aria-invalid="true"`); zero erros de JavaScript.
- **Contraste calculado (WCAG):** texto branco em `#047857` = **5,48:1**; texto `#ecfdf5` em `#065f46` = **7,29:1**. Ambos ultrapassam 4,5:1 para texto normal.
- **Screenshot:** `docs/evidence/UI_R6_ACCESSIBILITY_LOGIN_2026-11-26.png`.
- **Diff:** `git diff --check` passou.

## Resultado esperado versus obtido

| Verificação | Esperado | Obtido |
|---|---|---|
| Login por teclado | Campos e ações alcançáveis e erro relacionado | Passou no Playwright; foco percorreu e alerta ligado aos dois campos |
| Navegação e conteúdo | Landmarks nomeados e salto ao conteúdo | Passou em teste React Testing Library |
| Seletores de origem | Nome acessível para Tracker e Dirija Bem | Implementado em dois fluxos; compilação e suíte passaram |
| Foco visível | Não remover contorno sem alternativa | Regra global `:focus-visible`; estilos inline removidos |
| Contraste | Mínimo 4,5:1 para texto normal nos estados verificados | 5,48:1 e 7,29:1, medidos numericamente |
| Cerca e saúde | Axe automatizado nos componentes | Testes axe existentes incluídos na suíte de 98 testes |
| Leitor de tela e telas autenticadas | Operador percorre login, veículo, incidente, cerca e saúde com tecnologia assistiva | **Pendente de homologação humana**; não havia sessão autenticada disponibilizada para browser e não foi feita avaliação NVDA/VoiceOver |

## Limitações e decisão

R6 está concluída **somente no escopo automatizável desta máquina**. Os testes axe cobrem DOM em JSDOM; Playwright cobriu o login, não os fluxos internos autenticados. Não há evidência de avaliação com NVDA, VoiceOver ou operador. A cobertura completa de WCAG 2.2 AA não foi afirmada. QA/operação deve percorrer as telas internas por teclado e leitor de tela e registrar defeitos antes de qualquer piloto. O piloto permanece NO-GO.

## Próxima etapa

**Próxima etapa 7 de 8 — R7: exercício operacional e recuperação.** Ainda faltam R7 e R8 (2 etapas); a homologação humana de acessibilidade permanece um gate explícito para a decisão R8.
