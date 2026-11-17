# Validação — UI-4.1: catálogo de capacidades por protocolo/dispositivo

**Executada em:** 17/11/2026 (`America/Sao_Paulo`)  
**Etapa:** 12 de 74  
**Checkpoint anterior:** `84731b4`

## Resultado esperado

Manter um catálogo versionado e consultável que diferencie capacidades confirmadas,
indisponíveis e ainda desconhecidas por protocolo/modelo, sem anunciar sensor ou
comando físico que a integração atual não comprova.

## Resultado obtido

- As tabelas operacionais `capability_profiles` e `capability_profile_items` foram
  criadas no schema comum `monitoramento`, sem acoplar o catálogo ao banco Tracker
  ou ao Dirija Bem.
- Cada perfil possui protocolo, modelo, versão, estado ativo e justificativa; cada
  item possui direção, tipo, unidade, suporte explícito, evidência e restrições JSON.
- Perfis iniciais versão 1 foram cadastrados para Maxtrack, Suntech e Queclink.
- O catálogo só confirma campos efetivamente entregues pelos parsers atuais.
  `panic_signal` está indisponível e comandos remotos permanecem `unknown` até
  existir documentação e homologação do equipamento.
- A API somente leitura permite listar perfis e resolver o perfil mais específico,
  com fallback explícito para o modelo curinga e contrato
  `capability-catalog.v1`.
- Ausência de protocolo, perfil inexistente e falha do catálogo retornam erros
  estruturados; nenhum perfil é fabricado como fallback.

## Evidências

- Migration `023_create_capability_catalog.sql` aplicada no banco operacional e
  segunda execução em modo dry-run: **0 migrations pendentes**.
- Consulta real em processo pela API: **3 perfis**, **36 itens**, sendo **12 por
  protocolo**; resolução de Maxtrack, Suntech e Queclink retornou HTTP 200.
- Testes específicos do catálogo e do runner: **10 aprovados**, incluindo falha
  explícita do banco sem fallback inventado.
- Suíte backend completa: **249 aprovados e 12 pulados**.
- `git diff --check` sem erros de whitespace.

## Limitações e segurança

- Os perfis iniciais são por protocolo (`device_model='*'`). O mecanismo já prioriza
  perfil de modelo exato, mas ele só será cadastrado após documentação ou teste do
  hardware correspondente.
- `gps_valid` não é confirmado para Suntech/Queclink porque os parsers atuais fixam
  esse valor; altitude só é confirmada para Queclink.
- Este catálogo descreve capacidade. Ele não habilita detector, não envia comando
  e não equivale ao estado operacional de um sensor; essas separações pertencem às
  etapas UI-4.2, UI-4.3 e UI-4.6.
- Os 12 testes de integração opt-in permanecem pulados na suíte padrão e são
  executados apenas quando o ambiente de integração é explicitamente habilitado.

## Conclusão

**Aprovada.** A aplicação passou a possuir uma fonte operacional, versionada e
conservadora sobre aquilo que cada protocolo realmente suporta, sem dados mockados
e sem promessa de comandos ainda não comprovados.
