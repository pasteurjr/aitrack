# Validação — UI-0.6: bloqueio de rede hardcoded em componentes

**Executada em:** 17/11/2026 11:15 (`America/Sao_Paulo`)  
**Etapa:** 9 de 74

## Resultado esperado

Um teste automatizado deve falhar quando um componente introduzir `localhost`, IP literal, URL HTTP absoluta ou acesso HTTP fora do cliente compartilhado.

## Resultado obtido

- A fronteira estática agora varre todos os componentes TypeScript/TSX de produção.
- São rejeitados: URL `http/https` absoluta, IP literal, `localhost`, import direto de Axios e uso de `fetch`, inclusive com caminho relativo.
- Casos sintéticos provam que cada padrão proibido é realmente detectado; o teste não depende apenas do estado atual do repositório.
- A URL do provedor cartográfico foi removida de `MapComponent` e centralizada em `config/map.ts`, configurável por `REACT_APP_MAP_TILE_URL`.
- A base operacional da API continua permitida exclusivamente em `config/api.ts`.

## Evidências

- Busca estática em `src/components`: zero violações.
- Testes específicos de fronteira, configuração e mapa: **14 aprovados**.
- Suíte frontend completa: **72 aprovados**.
- TypeScript: aprovado.
- Build de produção: aprovado.

## Limitações

- O teste cobre componentes, onde novas chamadas de tela são introduzidas. Módulos de configuração mantêm URLs permitidas intencionalmente.
- Provedores externos ainda dependem da política de segurança de conteúdo do ambiente de implantação, fora desta etapa.

## Conclusão

**Aprovada.** A regressão por endereço direto em componentes passa a falhar automaticamente.
