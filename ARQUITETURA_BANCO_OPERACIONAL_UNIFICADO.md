# Banco operacional unificado

**Decisão:** criar o schema `monitoramento` como camada operacional comum ao
Tracker/AITrack e ao Dirija Bem. Os bancos de origem permanecem independentes e
não recebem tabelas de cercas, incidentes ou agentes.

## Responsabilidades

| Schema | Responsabilidade | Regra de escrita pela plataforma |
|---|---|---|
| `tracker` | ingestão e histórico da telemetria Tracker/AITrack | legado; manter durante a transição |
| `dirijabem` | viagens, posições e comportamento do Dirija Bem | leitura; simuladores existentes são a exceção |
| `monitoramento` | identidade canônica, cercas, incidentes, agentes, ações e auditoria | banco operacional da plataforma |

Uma cerca pertence ao veículo canônico de `monitoramento`, não ao banco que
forneceu uma posição. Toda evidência operacional conserva `fonte_codigo` para
explicar se veio de `tracker`, `dirijabem`, fusão ou ação do sistema.

## Identidade

O modelo anterior, `tracker.veiculo_unificado`, possui `device_id` e `codusu` na
mesma linha. Isso foi útil para a interface inicial, mas não representa o domínio
corretamente: `CODUSU` identifica um motorista/usuário do Dirija Bem, enquanto
um veículo da viagem é identificado principalmente por sua placa.

A migration 010 separa:

- `veiculos`: ativo canônico monitorado;
- `veiculo_identidades`: IDs de veículo, dispositivo e placa por fonte;
- `motoristas`: pessoa canônica;
- `motorista_identidades`: por exemplo, `CODUSU` do Dirija Bem;
- `veiculo_motorista_vinculos`: associação temporal entre ambos.

Não existem FKs para tabelas dos bancos-fonte. A plataforma guarda os
identificadores externos e resolve a identidade por integração, evitando que a
indisponibilidade ou mudança de um sistema de origem corrompa a operação comum.

## Implantação incremental

1. **UI-3.0A:** criar schema e modelo de identidade vazio.
2. **UI-3.0B:** criar runner rastreável e aplicar a migration com autorização.
   O runner registra nome e SHA-256 em `tracker.schema_migrations`, confirma o
   baseline legado antes de registrá-lo e nunca expõe a senha na linha de comando.
3. **UI-3.0C:** copiar identidades para o modelo novo, sem apagar a tabela antiga.
   `CODUSU` gera motorista; as placas das viagens geram veículos e vínculos
   temporais. A placa normalizada permite fusão futura com outra fonte.
4. **UI-3.0D:** fazer APIs lerem o modelo novo com fallback controlado.
5. **UI-3.0E1:** copiar monitores-base, incidentes e timeline preservando IDs.
6. **UI-3.0E2:** copiar atribuições, análises e alertas dos monitores.
7. **UI-3.0E3:** virar o runtime de incidentes e monitores para o operacional.
8. **UI-3.0F:** retirar o fallback depois dos testes dos dois simuladores e apps.
9. **UI-3.1:** criar cercas e versões geométricas em `monitoramento`.

Cada passo terá checkpoint próprio. Não haverá `DROP`, `TRUNCATE` ou alteração
destrutiva nas fontes durante essa transição.

## Estado da implantação

Em 06/11/2026, as etapas UI-3.0A, UI-3.0B e UI-3.0C foram concluídas. O schema
contém 26 veículos canônicos, 10 motoristas e 27 vínculos históricos. A aplicação
entrou em dupla leitura na UI-3.0D: por padrão, compara o modelo operacional com
o legado e ainda devolve os IDs antigos. A ativação definitiva aguarda a migração
de incidentes e atribuições de monitor da UI-3.0E.

### Modos de leitura

| Modo | Comportamento | Uso |
|---|---|---|
| `legacy` | lê somente `tracker.veiculo_unificado` | rollback operacional |
| `shadow` | lê ambos, compara e responde com legado | padrão durante a transição |
| `operational` | responde com `monitoramento`, com fallback configurável | após UI-3.0E |

Variáveis: `AITRACK_IDENTITY_READ_MODEL` e
`AITRACK_IDENTITY_ALLOW_FALLBACK`. O fallback pode ser desabilitado para falhar
de forma explícita quando a camada operacional se tornar a fonte oficial.

Na UI-3.0E1, as tabelas operacionais de monitores-base, incidentes e timeline
foram criadas. O runtime permanece no legado até que atribuições, análises e
alertas sejam copiados e a virada transacional possa ser validada em conjunto.

Na UI-3.0E2, dez atribuições Tracker foram convertidas em alvos canônicos do
tipo `vehicle`. O modelo também aceita alvo `driver`, necessário para monitorar
um usuário Dirija Bem independentemente dos veículos que ele conduziu. Os quatro
alertas seed sem análise não foram promovidos ao banco operacional.
