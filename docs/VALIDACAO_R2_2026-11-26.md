# R2 — inventário seguro para rotação de credenciais

**Data:** 26/11/2026 00:52 (`America/Sao_Paulo`)

**Checkpoint pré-etapa:** `f893995`

**Estado:** **em andamento — rotação aguarda DBA/infra**

## Resultado esperado

Credenciais expostas no histórico deixam de ser válidas; AITrack usa identidade de serviço
própria com privilégio mínimo; autenticação nova e rejeição da antiga são provadas sem
interromper outros sistemas.

## Inventário concluído

- `aitrackdatadrivr/config/.env` é a configuração do backend ativo; `config/.env` também existe
  para o projeto legado. Ambos definem as mesmas chaves `AITRACK_DB_*` e contêm a mesma
  credencial de banco. Valores não foram mostrados, copiados nem registrados.
- A configuração usa a classe de conta compartilhada documentada em `AGENTS.md`, com
  privilégios globais. O mesmo servidor hospeda mais de 35 sistemas; mudar a senha dessa conta
  diretamente pode interromper aplicações alheias ao AITrack.
- Auditoria de objetos alcançáveis por refs Git comparou a senha atualmente configurada em
  memória, sem imprimi-la: encontrou **177 versões de blobs em 18 caminhos**. O relatório grava
  somente contagens e caminhos, nunca o segredo. Esse resultado confirma que a senha em uso
  ainda está comprometida.
- A senha ativa foi removida do working tree atual: **49 ocorrências em 8 arquivos de texto**
  foram substituídas por `[REDACTED]`. `aitrackdatadrivr/scripts/security_audit.py` voltou a
  marcar **0 achados**. O scanner não lê arquivos `.env` ignorados e não limpa o histórico;
  portanto esse resultado não contradiz a exposição acima.

## Resultado obtido nesta etapa

O working tree foi sanitizado e o escopo/impacto estão identificados; nenhuma credencial de
ambiente ou banco foi alterado. R2 não pode ser marcado como concluído: a identidade atual é compartilhada globalmente e não há prova de
que os outros consumidores estejam prontos para uma troca coordenada.

## Procedimento necessário com DBA/infra

1. Inventariar todos os consumidores da conta global e seus bancos/horários de manutenção.
2. Criar identidade própria para AITrack, com acesso somente ao necessário em `tracker` e
   `monitoramento` e leitura em `dirijabem`; o DBA deve derivar privilégios de tabelas/ações do
   backend e das migrations, sem conceder `*.*`.
3. Entregar a nova credencial pelo cofre/canal operacional e atualizá-la diretamente no arquivo
   ignorado `aitrackdatadrivr/config/.env`; não enviar o valor por chat, commit, log ou ticket.
   Atualizar `config/.env` somente se o serviço legado tiver consumidor confirmado.
4. Validar conexão e fluxos de leitura/escrita permitidos com o novo usuário; confirmar que
   escritas fora dos schemas autorizados e leituras/escritas não permitidas falham.
5. Após todos os consumidores migrarem, trocar/revogar a senha antiga da conta global, provar
   que a antiga falha e acompanhar serviços dependentes. Registrar evidência sem segredo.
6. Avaliar limpeza do histórico Git depois da revogação, coordenando clones, forks e consumidores;
   não fazer reescrita de histórico/force-push nesta etapa sem janela e coordenação.

## Limitações e gates

- A criação de usuário, concessão/revogação de privilégios e troca de senha afetam o servidor
  MySQL compartilhado e excedem o escopo de escrita do agente descrito em `AGENTS.md`.
- Não foi aberta conexão remota nem executado SQL. A etapa depende de DBA/infra e do inventário
  dos demais sistemas consumidores.
- **R2 permanece aberto; o piloto continua NO-GO.** Depois que DBA/infra atualizar o arquivo
  ignorado com a nova identidade, a próxima execução pode validar conexão, escopo e rejeição
  da credencial anterior sem revelar nenhum valor.
