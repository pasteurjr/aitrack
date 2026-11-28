# Exercício operacional R7 — roteiro para homologação

**Objetivo:** verificar se a equipe consegue detectar, conter, recuperar e reconciliar uma interrupção do AITrack + DataDrivr sem ajuda do desenvolvedor.

## Participantes e regras

- **Operador 1:** faz a triagem de incidente e mantém a comunicação com o supervisor.
- **Operador 2:** monitora Tracker/Dirija Bem, filas, evidências e reconciliação.
- **Supervisor:** autoriza modo seguro, restart/rollback e retomada; registra decisões.
- **Facilitador:** injeta os eventos sintéticos e anota horários. Não dá instruções durante o exercício.
- Usar homologação isolada, veículos e contatos sintéticos, canais em sandbox e backup descartável. Não usar credenciais ou dados de produção.

## Metas propostas para aceite

Estas metas são sugestões para deliberação da operação e ainda não foram aprovadas.

| Métrica | Proposta | Como medir |
|---|---:|---|
| RTO da API e workers essenciais | até 15 minutos | Da declaração de indisponibilidade até `live` e `ready`, workers saudáveis e triagem restabelecida |
| RPO de eventos já confirmados | 0 registros | Comparar IDs/correlation IDs confirmados antes da falha com a restauração |
| Duplicidade após replay | 0 ações/incidentes duplicados | Contar por idempotency key e correlation ID após reconciliação |
| Ação externa no ensaio | 0 entregas | Confirmar somente recibos sandbox e logs locais |
| Decisão do supervisor | até 5 minutos em SEV-1 | Medir do alerta até takeover/modo seguro |

RPO zero só vale para registros cuja confirmação já foi enviada ao produtor. Eventos ainda em trânsito devem aparecer como pendentes e ser reenviados pelo simulador.

## Preparação

1. Registrar data, versão, commit, facilitador, participantes e contatos de plantão.
2. Verificar selo de simulação, isolamento da rede, sandbox, ausência de destinatários reais e backup sintético restaurável.
3. Capturar contagens por origem, incidentes, ações, receipts, leases e dead-letter. Guardar os IDs sintéticos.
4. Confirmar que há procedimento para interromper o exercício imediatamente e voltar ao estado inicial.

## Cenários conduzidos sem ajuda

| Cenário | Injeção do facilitador | Ação esperada | Evidência de aprovação |
|---|---|---|---|
| 1. Tracker indisponível | Suspender pacotes sintéticos por 3 minutos | Operador separa falha de origem de veículo offline, abre incidente técnico e monitora a recuperação | Um incidente da fonte, sem incidentes falsos para toda a frota |
| 2. Dirija Bem atrasado | Pausar avanço do cursor sintético | Indicar dados desatualizados, preservar dados recebidos e reconciliar pelo cursor | Totais recebidos = processados + rejeitados explicados + pendentes |
| 3. Agente degradado | Fazer o provider sintético expirar | Fallback seguro e revisão humana, sem comunicação externa | Decisão auditada e zero envio real |
| 4. Concorrência | Dois operadores alteram a mesma versão do incidente | Uma alteração vence; a outra recebe conflito, recarrega e decide se reaplica | Nenhuma sobrescrita silenciosa |
| 5. Reinício | Parar API/worker pelo supervisor | Reiniciar, verificar live/ready e workers antes de liberar a fila | RTO medido, sem regressão de estado |
| 6. Restauração | Substituir a instância de homologação por backup conhecido | Validar checksum, iniciar serviço, reconciliar receipts/incidentes/ações | RPO medido, contagens e IDs explicados |
| 7. Rollback | Implantar artefato de exercício e reverter para o anterior | Conferir compatibilidade de schema e health antes de reativar workers | Versões registradas e serviço pronto |
| 8. Fila após falha | Deixar duas ações sintéticas com lease expirado | Recuperar uma para retry e outra para dead-letter pelo limite de tentativas | Processamento idempotente, nenhuma duplicata |

## Critérios de interrupção

Interromper, desabilitar workers pelo procedimento de homologação e chamar o supervisor se ocorrer qualquer acesso a alvo externo, entrega real, perda sem explicação, duplicação, inconsistência de identidade ou incapacidade de restaurar o estado seguro.

## Registro preenchível

| Campo | Preencher no exercício |
|---|---|
| Data, janela e ambiente | |
| Commit e artefato | |
| Operador 1 / Operador 2 / Supervisor / Facilitador | |
| RTO observado / meta aceita por | |
| RPO observado / meta aceita por | |
| IDs e contagens antes/depois | |
| Cenários aprovados / reprovados | |
| Desvios e ações corretivas com responsável/prazo | |
| Confirmação de zero contato e comando real | |
| Assinatura do supervisor e responsável operacional | |

**Aprovação formal:** permanece pendente até o exercício ocorrer com as pessoas responsáveis e as metas RTO/RPO serem aceitas pela operação.
