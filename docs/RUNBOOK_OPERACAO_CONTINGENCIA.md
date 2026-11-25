# Runbook de operação e contingência — AITrack + DataDrivr

**Revisão:** 1 · **Aplicação:** backend `aitrackdatadrivr` · **Portas:** API 5009, TCP 9000, App 1 3001, App 2 3003

Este documento orienta a operação técnica. O teste com operadores reais e a aprovação
formal de plantão continuam requisitos separados antes de qualquer piloto.

## 1. Papéis e severidade

| Severidade | Exemplo | Ação inicial |
|---|---|---|
| SEV-1 | vazamento, tenant cruzado, comando indevido, perda irrecuperável | suspender automações/canais; acionar responsável técnico e privacidade |
| SEV-2 | API/ingestão indisponível, fila crítica sem drenagem | modo seguro, diagnóstico e escalonamento ao plantão |
| SEV-3 | IA degradada, um provedor/canal fora, relatório atrasado | fallback, fila e próximo horário de revisão |
| SEV-4 | aviso não crítico ou latência isolada | registrar e acompanhar tendência |

Contatos devem ser mantidos no diretório operacional da empresa, não neste repositório.

## 2. Pré-requisitos e configuração

- Python e dependências conforme `AGENTS.md` §3.
- Node para interfaces.
- Segredos injetados por ambiente/cofre; nunca exibir o `.env` no terminal ou anexá-lo.
- `AITRACK_OPERATION_MODE=production` em implantação produtiva; TLS termina no proxy aprovado.
- `AITRACK_COOKIE_SECURE=true` quando TLS está ativo.
- Banco operacional somente nos schemas autorizados pelas regras do repositório.

## 3. Subida controlada

Execute cada serviço em terminal/unidade supervisionada própria, a partir de
`aitrackdatadrivr/`:

```bash
python run.py
python simulator.py                 # somente ambiente de demonstração
python dirijabem_continuous_simulator.py --drivers 5 --speed 10  # somente demonstração
```

Frontends em terminais separados:

```bash
cd frontend && PORT=3001 BROWSER=none npm start
cd aitrackdatadrivr/frontend && PORT=3003 BROWSER=none npm start
```

Em produção, use o supervisor de processos homologado, sem `debug=True`. Registre versão,
hash do deploy e operador responsável.

## 4. Health e prontidão

```bash
curl -fsS http://127.0.0.1:5009/api/health/live
curl -i http://127.0.0.1:5009/api/health/ready
```

`live` confirma que o processo responde. `ready` HTTP 503 exige consultar dependências e
o painel autenticado `/api/health/integrations`. Métricas `/api/metrics` e detalhes
requerem sessão com `health.read`.

## 5. Parada segura e identificação de processo

Identifique processo apenas nas portas deste projeto e confirme o comando/PID antes de
encerrar:

```bash
ss -ltnp | rg ':(5009|9000|3001|3003)\b'
ps -p PID -o pid=,comm=,args=
kill PID
```

Substitua `PID` pelo número validado. Não use kill por nome, wildcard ou grupo. Não
encerre processos nas portas 3000/3002, usadas por outros projetos.

## 6. Integração Tracker ou Dirija Bem sem dados novos

1. Confira estado e último sucesso em `/api/health/integrations`.
2. Compare hora do último pacote/offset com a origem e relógio do banco.
3. Se a integração inteira estiver parada, registre incidente técnico da fonte; não
   atribua offline individual a todos os veículos.
4. Após retorno, verifique quarentena, receipts e offset; replay deve ser idempotente.
5. Compare recebidos = persistidos + rejeitados explicados + pendentes.
6. Banco Dirija Bem continua somente leitura para APIs operacionais; simulador usa seu
   fluxo de escrita documentado apenas em ambiente de demonstração.

## 7. Fila crescente, leases e dead-letter

1. Consulte saúde do worker, profundidade e item mais antigo.
2. Diferencie `pending`, `claimed` com lease válido, lease vencido e `dead`.
3. Reinicie worker pelo supervisor aprovado; não reenvie linhas manualmente.
4. Reivindique leases vencidos pelo mecanismo da aplicação e preserve idempotency key.
5. Dead-letter requer classificação de causa e aprovação antes de reprocessar.
6. Confirme duplicatas zero e backlog drenando antes de reabrir automação.

## 8. IA ou canal indisponível

- IA: circuit breaker e fallback seguro encaminham para revisão humana.
- Mensagem/voz: respeite opt-out, cooldown, limite de tentativa e sandbox durante teste.
- Se estado/autoridade da ação não forem claros, pause execução autônoma pelo mecanismo
  administrativo autenticado e acione operador/supervisor.
- Não altere chaves ou URL de provedor por edição no código; use cofre e processo de rotação.

## 9. Modo seguro e takeover

1. Supervisor assume incidentes críticos e pausa o agente associado.
2. Registre ator, motivo, horário, versão do incidente e correlação.
3. Confirme visualmente que novas ações do agente estão bloqueadas.
4. Mantenha apenas leitura e triagem humana enquanto houver risco desconhecido.
5. Comandos físicos e notificações de alto impacto permanecem sujeitos a dupla aprovação.

## 10. Reinício e reconciliação

1. Salve versão/hash e snapshot de contagens, sem copiar dados pessoais desnecessários.
2. Reinicie serviço pelo supervisor usando o PID/unidade exatos.
3. Aguarde `live`; confirme `ready` e cada worker crítico.
4. Reconcile receipts, incidentes, ações, versões e dead-letter por correlation ID.
5. Verifique que estados terminais não regrediram, duplicidade é zero e backlog drena.
6. Registre RTO, registros perdidos (meta 0), duplicatas e desvios.

## 11. Deploy e rollback de aplicação

- Registre commit, artefato, configuração identificada por versão e migration pendente.
- Deploy deve usar pacote imutável e health gate.
- Rollback de aplicação: volte ao artefato anterior pelo supervisor/deployment tool,
  confirme contrato de schema compatível e teste health antes de reabilitar workers.
- Não reverta migration com `DROP`, `TRUNCATE` ou edição manual sem plano específico,
  backup verificado e dupla revisão.
- Nesta revisão não foi executado rollback em ambiente de produção; ensaiar em
  homologação isolada antes do piloto.

## 12. Backup, restauração e credenciais

- Backup/restauração seguem procedimento do DBA e aprovação do proprietário do banco.
- Verifique destino, schema, criptografia, checksum e retenção antes de restaurar.
- Não imprimir senhas na linha de comando nem salvar dump com dados reais no Git.
- Rotação: criar nova credencial de privilégio mínimo, atualizar cofre, validar conexão,
  revogar a anterior e guardar evidência sem o valor secreto.

## 13. Incidente de segurança ou privacidade

1. Suspenda automações e exportações afetadas.
2. Preserve logs/auditoria e anote request/correlation IDs; não copie tokens ou conteúdo
   integral de contatos/áudio para tickets.
3. Acione os papéis de segurança, privacidade e operação no diretório oficial.
4. Contenha acesso (sessões/credenciais) por procedimento aprovado e registre horário.
5. Avalie alcance, finalidade e titulares com responsável de privacidade/jurídico.
6. Retome apenas após evidência de contenção, rotação, teste e autorização formal.

## 14. Retorno à operação e registro pós-incidente

Supervisor confirma readiness, reconciliação, filas, canais e opt-outs; reabilita ações em
ordem de risco. Registre timeline, causa, impacto, dados afetados, ações, validações,
tempos, responsáveis e riscos restantes. Faça revisão pós-incidente em até um dia útil.

## 15. Limites desta revisão

Este runbook passou por verificação estática e possui comandos restritos. Um operador que
não desenvolveu o sistema ainda precisa executar o exercício em homologação, incluindo
diagnóstico sorteado, modo seguro, restart, rollback de aplicação e reconciliação. TLS,
backup/restore e contatos também dependem de ambiente/autoridade externa.
