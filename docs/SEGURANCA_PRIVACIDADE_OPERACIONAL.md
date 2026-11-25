# Segurança e privacidade operacional

## Escopo e princípios

O sistema trata telemetria veicular, identidade de motorista, contatos, incidentes,
decisões de agentes e auditoria. A operação deve observar finalidade, necessidade,
menor privilégio, isolamento por empresa, rastreabilidade e retenção limitada. Dados de
Tracker e Dirija Bem permanecem vinculados ao tenant e não devem ser enviados integralmente
a provedores de IA ou canais externos.

## Inventário mínimo

| Categoria | Finalidade | Acesso | Retenção proposta |
|---|---|---|---:|
| posição e sensores | rastreamento, cerca, rota e segurança | operador autorizado | 180 dias |
| eventos de condução | risco e coaching | operador/supervisor | 365 dias |
| incidentes e ações | atendimento e prova operacional | operador/auditor | 5 anos |
| decisão/prompt mínimo de IA | explicabilidade e qualidade | supervisor/auditor | 180 dias |
| contato e consentimento | comunicação autorizada | operador restrito | vigência + 90 dias |
| áudio/transcrição | somente com base legal e consentimento | papel específico | 30 dias |
| auditoria e segurança | investigação e conformidade | auditor | 5 anos |
| logs técnicos | disponibilidade e diagnóstico | plataforma | 90 dias |
| exportações | finalidade solicitada | solicitante autorizado | 7 dias |

Os prazos são proposta técnica e exigem aprovação jurídica/contratual antes do piloto.

## Controles obrigatórios

- sessão opaca, CSRF, RBAC e tenant derivados no servidor;
- TLS para aplicação, banco e provedores; cookie Secure em produção;
- segredo somente por ambiente/cofre, com rotação e revogação documentadas;
- payload mínimo para IA; telefone, e-mail, áudio e transcrição são redigidos de logs;
- opt-out impede novas comunicações, salvo obrigação legal documentada;
- exportação registra filtros, tenant, ator e expira automaticamente;
- acesso, correção, anonimização e exclusão devem possuir procedimento e evidência;
- incidente de privacidade interrompe automação e aciona o runbook.

## Subprocessadores e decisão humana

Provedores de IA, mensagem e voz só podem ser habilitados após contrato, região de dados,
retenção, treinamento com dados do cliente e mecanismo de exclusão serem avaliados. A IA
recomenda e executa apenas ações reversíveis dentro da política; comando físico, autoridade
pública e comunicação de alto impacto permanecem sujeitos a aprovação humana distinta.

## Gates ainda externos ao repositório

- rotação comprovada das credenciais que já apareceram no histórico Git;
- DAST autenticado em homologação HTTPS;
- validação de TLS e backup criptografado;
- aprovação jurídica dos prazos e bases legais;
- plano de resposta a titulares e incidente de dados testado por responsável nomeado.
