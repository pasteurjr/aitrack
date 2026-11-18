# Validação — UI-5.3: decisão estruturada da IA

**Executada em:** 18/11/2026 03:26 (`America/Sao_Paulo`)  
**Etapa:** 26 de 74  
**Checkpoint anterior:** `1e5803d`  
**Commit de implementação:** `9c931c3`

## Resultado esperado

Definir e validar um contrato com classificação, confiança, evidências, risco,
ações propostas e necessidade humana, impedindo que texto livre execute ações.

## Resultado obtido

- O contrato `vehicle-monitoring-decision.v1` foi publicado como JSON Schema e
  implementado por validador determinístico no backend.
- Classificação aceita apenas normal, atenção, suspeita, incidente confirmado ou
  evidência insuficiente; confiança fica entre 0 e 1.
- Risco possui nível, score 0–100 e justificativa. Alto/crítico exige revisão
  humana obrigatória.
- Toda decisão exige de uma a vinte evidências com origem Tracker, Dirija Bem,
  fusão, sistema ou operador, tipo, referência e resumo.
- Ações são explicitamente `proposed_actions`. Autoridades e comando veicular
  sempre exigem aprovação; campo extra como `executed` é rejeitado.
- Evidência insuficiente exige revisão humana. Prazo humano é limitado a 24 h.
- Decisão válida é serializada de forma canônica, recebe SHA-256 e timestamp de
  validação antes de entrar no ledger.

## Evidências

- Migration `034_structure_agent_decisions.sql` aplicada; runner repetido:
  **0 migrations pendentes**.
- Prova MariaDB persistiu uma decisão `suspected_incident`, formato v1, timestamp e
  hash `240a3840447f...`, conferido contra o JSON canônico.
- A mesma decisão alterada para `request_vehicle_command` sem aprovação foi
  recusada antes da persistência.
- Rollback confirmou **zero execuções/decisões sintéticas residuais**.
- Testes cobrem ordem do JSON, campos extras, confiança, risco, evidência vazia,
  data inválida, revisão humana e ações sensíveis.
- **20 testes combinados** e **364 testes backend** aprovados; 12 integrações opt-in
  puladas.

## Limitações e segurança

- O schema garante forma e invariantes de segurança, não veracidade semântica. A
  evidência referenciada será resolvida/auditada pelas ferramentas e worker futuros.
- Nenhum modelo é chamado nesta etapa e nenhuma proposta é executada.
- Contato com proprietário, mensagem, ligação, autoridades e comando serão tratados
  por filas/políticas próprias; a decisão da IA não ignora esses controles.
- Casos dourados, calibração de confiança e falsos positivos/negativos pertencem à
  etapa de avaliação do runtime.

## Conclusão

**Aprovada.** Uma resposta livre de modelo não pode mais ser confundida com decisão
operacional válida; somente o contrato v1 validado entra no ledger.
