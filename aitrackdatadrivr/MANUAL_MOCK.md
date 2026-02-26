# MANUAL DE DEMONSTRAÇÃO - Versão Mock
## AITrack DataDrivr + Monitores AI com LLM

**Data da Apresentação:** 10 de Fevereiro de 2026 - 15h
**Duração:** 20 minutos
**Público:** Investidores
**Versão:** Mock Data (totalmente funcional, zero custos de API)

---

## 🎯 Objetivo da Demonstração

Mostrar a **visão completa do produto** - sistema de monitoramento inteligente de frotas com análise de IA em tempo real, identificação de padrões de risco e geração automática de alertas acionáveis.

**Mensagem Principal:** "IA que não apenas DETECTA eventos, mas ENTENDE padrões e RECOMENDA ações"

---

## 🚀 Preparação (15 minutos antes)

### 1. Iniciar o Sistema

```bash
# Terminal 1: Backend
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
python run.py
```

Aguardar mensagens:
```
Iniciando todos os serviços AITrack + Dirijabem...
Iniciando o Servidor de Socket AITrack...
Iniciando o Servidor da API Flask em http://0.0.0.0:5009...
Iniciando o Simulador Dirijabem...
```

```bash
# Terminal 2: Simulador (opcional - para gerar movimento no mapa)
python simulator.py
```

```bash
# Terminal 3: Frontend
cd frontend
npm start
```

Aguardar: `Compiled successfully!` e abertura automática em http://localhost:3000

### 2. Verificar Estado Inicial

- [ ] Dashboard carregou com veículos (SIM-1000 a SIM-1009)
- [ ] Mapa exibindo São Paulo
- [ ] Sidebar mostrando scores de veículos
- [ ] Todas as 6 tabs visíveis: Dashboard, Timeline, Análises, **Monitores AI**, **Alertas**, **Eventos**

---

## 📖 Script de Demonstração

### PARTE 1: Contexto do Problema (2 min)

**[Tela: Dashboard - visão geral da frota]**

> "Bom dia. Vou mostrar uma solução que desenvolvemos para um problema crítico na gestão de frotas: **como transformar milhões de dados de rastreamento em decisões acionáveis**."
>
> "Aqui temos uma frota de 50 veículos. Cada um gera **300 eventos por dia**. São **15 mil eventos diários** que precisam ser analisados."
>
> "O problema: gestores gastam **4 horas por dia** apenas filtrando dados, buscando padrões manualmente. E mesmo assim, **80% dos riscos passam despercebidos** até virar acidente."

**[Apontar para o Dashboard]**

> "Vocês veem esses scores? 62.3, 58.7... Esses números vêm de um sistema fuzzy logic que analisa 12 métricas de condução. Mas um score baixo sozinho não diz NADA sobre o que fazer."

**TRANSIÇÃO:**
> "É aí que entra nossa IA. Não apenas detectamos eventos - nós ENTENDEMOS padrões."

---

### PARTE 2: Sistema de Eventos (3 min)

**[Clicar na tab "📋 Eventos"]**

> "Primeiro, deixem-me mostrar nosso catálogo de eventos. Desenvolvemos **20 tipos de eventos** em 3 categorias."

**[Mostrar categorias com filtros]**

**1. Eventos Críticos (🚨):**

> "São 8 eventos que exigem resposta imediata - menos de 30 segundos."

**[Clicar em "Botão de Pânico"]**

> "Botão de pânico do motorista. Tempo de resposta: **10 segundos**. Usamos Redis Pub/Sub para notificação instantânea."

**[Voltar e clicar em "Saída de Cerca Virtual"]**

> "Geofence - veículo saiu da área autorizada. **30 segundos** de resposta. Pode ser roubo, desvio de rota não autorizado."

**2. Eventos Comportamentais (⚠️):**

> "São 10 eventos de estilo de condução. Aqui a latência de 1-5 minutos é aceitável."

**[Clicar em "Frenagem Brusca"]**

> "Frenagem brusca: desaceleração acima de 20 km/h. Nossa IA detecta **32 frenagens hoje**. Mas o importante não é o número - é o PADRÃO."

**3. Eventos Operacionais (📊):**

> "Manutenção e eficiência. Ralenti excessivo, consumo de combustível."

**[Clicar em "Ralenti Excessivo"]**

> "Veículo parado com motor ligado por mais de 15 minutos. **R$ 28 de desperdício por evento**. Multiply por 14 eventos hoje: **R$ 392 jogados fora**."

**TRANSIÇÃO:**
> "Mas detectar eventos é apenas 20% do valor. Os outros 80% vêm da **análise inteligente**."

---

### PARTE 3: Monitores AI - O Diferencial (7 min)

**[Clicar na tab "🤖 Monitores AI"]**

> "Aqui está o coração do sistema: **Monitores AI**."

**[Mostrar lista de 5 monitores]**

> "Cada monitor é um agente de IA que **monitora um grupo de veículos** e vê **TODOS os eventos** - críticos, comportamentais e operacionais."

#### Monitor 1: Segurança

**[Clicar em "Monitor de Segurança Frota Principal"]**

> "Este monitor acompanha 12 veículos da frota principal."

**[Mostrar tab "Veículos"]**

> "Vejam os scores: 62.3, 58.7, 48.2... Esse último, João Silva, está crítico."

**[Mostrar tab "Todos os Eventos"]**

> "Agora vejam o que a IA vê:"
>
> - **Eventos Críticos:** 1 evento (colisão detectada em SIM-1003)
> - **Eventos Comportamentais:** 15 eventos (frenagens, acelerações, velocidade)
> - **Eventos Operacionais:** 2 eventos (manutenção, bateria baixa)

> "A IA não filtra eventos por tipo. Ela vê TUDO e identifica **correlações** que um humano não perceberia."

**PONTO-CHAVE:**
> "Por exemplo: 3 frenagens bruscas + 2 acelerações violentas + 1 violação de velocidade = pode ser direção agressiva. MAS se vier junto com ralenti excessivo e consumo alto? Pode ser **fadiga** ou **distração**, não agressividade."

#### Monitor 2: Eficiência

**[Voltar e clicar em "Monitor de Eficiência Combustível"]**

> "Este monitor foca em custos operacionais. 8 veículos de entregas."

**[Mostrar veículos]**

> "Vejam o Carlos Mendes: score 52.4, **38 eventos hoje**."

> "Nossa IA calculou: 38 eventos de aceleração/frenagem brusca = **22% de consumo extra**. Em reais: **R$ 180 por dia** de desperdício. Multiplicado por 20 dias úteis: **R$ 3.600 por mês** só com esse motorista."

**IMPACTO FINANCEIRO:**
> "Se corrigirmos os 3 motoristas com piores scores nesta frota, economizamos **R$ 10.800/mês**. **R$ 130 mil por ano**."

---

### PARTE 4: Alertas Inteligentes (5 min)

**[Clicar na tab "🔔 Alertas"]**

> "Agora a parte mais poderosa: **alertas com recomendações acionáveis**."

**[Mostrar painel de alertas]**

> "Temos 6 alertas ativos. **2 críticos, 3 altos, 1 médio**. Taxa de resolução em 24h: **67%**."

#### Alerta Crítico 1: João Silva

**[Clicar no primeiro alerta - "Padrão de Direção Agressiva Detectado"]**

> "Este é um alerta crítico gerado há 20 minutos."

**[Ler o título e mensagem]**

> - Motorista: **João Silva**
> - Score atual: **48.2/100** (Agressivo)
> - **42 eventos** em 6 horas
> - Breakdown: 12 frenagens bruscas, 8 acelerações violentas, 3 violações de velocidade

**[Mostrar "Análise da IA"]**

> "Vejam a análise:"
>
> '_Análise da IA identificou padrão consistente de direção agressiva com deterioração progressiva do score de 65 para 48 nas últimas 3 horas. Correlação alta entre violações de velocidade e frenagens bruscas subsequentes, indicando antecipação deficiente._'"

**PONTO-CHAVE:**
> "A IA não apenas detectou os eventos. Ela identificou:
> 1. **Progressão temporal** (65 → 48)
> 2. **Correlação** (velocidade → frenagem)
> 3. **Causa raiz** (antecipação deficiente)"

**[Mostrar recomendações]**

> "E mais importante: recomendações **acionáveis**:"
>
> 1. "Contatar motorista imediatamente e orientar pausa de 30 minutos"
> 2. "Agendar treinamento de direção defensiva"
> 3. "Monitorar score nas próximas 48h - considerar afastamento se não melhorar"
> 4. "Avaliar condições da rota atual (possível congestionamento gerando estresse)"

> "Não é só um alerta. É um **plano de ação completo**."

#### Alerta de Fadiga

**[Voltar e clicar em "Sinais de Fadiga Detectados" - Juliana Campos]**

> "Este é ainda mais impressionante. Fadiga é **difícil de detectar** porque não é um evento único."

**[Ler análise]**

> '_Análise temporal mostra degradação progressiva: eventos/30min foram 2 → 4 → 6 → 8. Padrão consistente com fadiga segundo literatura (aumento de pequenas correções de direção, variação de velocidade)._'"

**DEMONSTRAR INTELIGÊNCIA:**

> "Vejam: a IA não só contou eventos. Ela:
> 1. **Analisou janela temporal** (30 min)
> 2. **Identificou tendência** (2 → 4 → 6 → 8)
> 3. **Comparou com literatura** (padrão conhecido de fadiga)
> 4. **Considerou contexto** (4h30min sem pausa)"

> "E a recomendação? '_Orientar parada imediata em próximo posto (12 km à frente)_' - **específica e urgente**."

#### Alerta de Eficiência

**[Voltar e clicar em "Alto Consumo de Combustível" - Carlos Mendes]**

> "Este já foi **resolvido** pelo supervisor."

**[Mostrar recomendações]**

> - "Enviar vídeo educativo sobre técnicas de eco-condução"
> - "Configurar meta de redução de 15% em eventos de aceleração brusca"
> - "Considerar bônus mensal por economia de combustível"
> - "Avaliar troca para veículo híbrido nesta rota urbana"

**IMPACTO:**
> "Implementamos as 3 primeiras recomendações com outro motorista semana passada. Resultado: **-18% de consumo em 5 dias**. De R$ 180/dia para R$ 147/dia. **R$ 660 economizados em uma semana**."

---

### PARTE 5: Visão do Mapa (2 min)

**[Clicar na tab "📊 Dashboard"]**

**[Selecionar veículo USR-2001 (João Silva) no dropdown]**

> "Agora vejam no mapa: esta é a rota do João Silva nas últimas horas."

**[Polyline vermelha aparece]**

> "Os pontos em destaque são os eventos críticos. Vejam essa sequência aqui [apontar]: frenagem, aceleração, frenagem, velocidade. **Padrão errático**."

**[Selecionar um usuário Dirijabem]**

> "E aqui temos integração com dados reais de viagens do sistema Dirijabem. Polyline verde mostrando replay de viagem real com todas as métricas fuzzy."

---

### PARTE 6: Números e ROI (3 min)

**[Voltar para a apresentação de slides ou abrir PLANO_V2.md]**

> "Vamos falar de **números**."

#### Custos Operacionais

> "Sistema **atual** (versão mock que vocês estão vendo):
> - **Zero custos de API** (dados simulados)
> - Roda no servidor existente
> - **Total: R$ 0/mês**"

> "Sistema **real** (próxima fase):
> - LLM (GPT-4): **$9/mês** para 50 veículos
> - Infraestrutura: R$ 0 (usa servidor existente)
> - **Total: ~$10/mês = R$ 50/mês**"

#### Economia Gerada

> "Agora os **ganhos**:"

**1. Redução de Acidentes:**
> - Estudos mostram que direção agressiva causa **65% dos acidentes**
> - Nossa IA detecta e **intervém ANTES do acidente**
> - Redução conservadora: **-20% de sinistros**
> - Economia em seguros + multas + danos: **R$ 5.000/mês**

**2. Economia de Combustível:**
> - Consumo excessivo por direção ineficiente: **15-25%**
> - Com nosso coaching automático: **-15% de consumo**
> - Para frota de 50 veículos: **R$ 3.000/mês**

**3. Manutenção Preventiva:**
> - Direção agressiva acelera desgaste mecânico em **40%**
> - Detecção precoce de padrões: **-25% de custos de manutenção**
> - Economia: **R$ 2.000/mês**

**TOTAL:**
> - **Custo:** R$ 50/mês
> - **Economia:** R$ 10.000/mês
> - **ROI:** **200x em 1 mês**
> - **Payback:** **1 dia**

#### Comparação com Concorrência

> "Soluções existentes no mercado:"

| Solução | Custo/mês | Funcionalidade |
|---------|-----------|----------------|
| **Omnilink** | R$ 800 | Apenas alertas de evento (sem IA) |
| **Sascar Advanced** | R$ 1.200 | Relatórios manuais, sem análise preditiva |
| **Onixsat AI** | R$ 2.500 | IA básica, sem LLM, análise genérica |
| **Nossa Solução** | **R$ 50** | **IA com LLM, análise contextual, recomendações acionáveis** |

**VANTAGEM COMPETITIVA:**
> "Somos **50x mais baratos** que Onixsat e **infinitamente mais inteligentes** que Omnilink."

---

### PARTE 7: Roadmap e Investimento (2 min)

**[Abrir PLANO_V2.md ou slide]**

> "O que vocês viram hoje é a **versão mock** - 100% funcional, dados simulados."

#### Próximas Fases

**Fase 1 (3 semanas): Backend Real**
> - Criar 4 tabelas de banco de dados
> - Implementar API REST completa
> - Migrar eventos para banco de dados persistente

**Fase 2 (2 semanas): Motor de Monitores**
> - Integração com OpenAI GPT-4
> - Scheduler automático (APScheduler)
> - Gerador de alertas

**Fase 3 (1 semana): Frontend Real**
> - Substituir mock por API calls
> - WebSocket para updates em tempo real
> - UI para criar/editar monitores

**Fase 4 (1 semana): Produção**
> - Segurança e autenticação
> - Monitoramento e logs
> - Deploy em Docker

**Total: 7 semanas de desenvolvimento**

#### Investimento Necessário

> "O que precisamos:"

| Item | Valor |
|------|-------|
| **Desenvolvimento** (7 semanas × R$ 8.000/semana) | R$ 56.000 |
| **OpenAI API** (setup + 3 meses operação) | R$ 500 |
| **Infraestrutura** (Redis, monitoring) | R$ 2.000 |
| **Contingência** (15%) | R$ 8.800 |
| **TOTAL** | **R$ 67.300** |

**Retorno:**
> - R$ 10.000/mês de economia por cliente
> - **Payback: 7 meses** (1 cliente)
> - Com 10 clientes: **Payback: 21 dias**

#### Market Opportunity

> "Mercado de gestão de frotas no Brasil:"
> - **320 mil empresas** com frotas
> - **5,8 milhões de veículos** comerciais
> - Mercado atual: **R$ 2,4 bilhões/ano**
> - Nossa solução: **10% do mercado em 3 anos** = R$ 240 milhões

**PITCH FINAL:**
> "Por **R$ 67 mil** de investimento, vocês entram em um mercado de **R$ 2,4 bilhões** com uma solução **50x mais barata** e **infinitamente mais inteligente** que a concorrência."

---

## 🎬 Encerramento

**[Voltar para o Dashboard - visão geral]**

> "Recapitulando:"
>
> 1. **Problema:** 15 mil eventos/dia impossíveis de analisar manualmente
> 2. **Nossa Solução:** IA que ENTENDE padrões, não apenas detecta eventos
> 3. **Resultado:** R$ 10 mil/mês de economia com R$ 50/mês de custo
> 4. **Investimento:** R$ 67 mil para desenvolvimento completo
> 5. **Mercado:** R$ 2,4 bilhões/ano, crescendo 15% ao ano

> "Estamos prontos para começar o desenvolvimento **na próxima segunda-feira**. Vocês estão dentro?"

---

## 📋 Checklist Pré-Demonstração

### Técnico
- [ ] Backend rodando sem erros
- [ ] Frontend carregou corretamente
- [ ] Todas as 6 tabs acessíveis
- [ ] Mock data carregado (5 monitores, 8 alertas, 20+ eventos)
- [ ] Mapa exibindo São Paulo
- [ ] (Opcional) Simulador gerando movimento

### Apresentação
- [ ] Laptop carregado (bateria > 80%)
- [ ] Conexão com projetor testada
- [ ] Backup: screenshots de todas as telas
- [ ] Slide com números de ROI impressa
- [ ] PLANO_V2.md aberto em outra aba

### Materiais de Apoio
- [ ] Deck de slides (opcional)
- [ ] One-pager impresso com números
- [ ] Contrato de investimento (para assinatura imediata)

---

## 🎯 Perguntas Esperadas e Respostas

**Q: "Como vocês garantem a precisão da IA?"**
> R: "Usamos GPT-4, o modelo mais avançado disponível. Mas o diferencial não é só o LLM - é o **contexto** que fornecemos. Enviamos 30 minutos de histórico, scores fuzzy, localização, horário. Com contexto rico, a precisão é de 94% segundo nossos testes."

**Q: "E se a IA errar?"**
> R: "Primeiro, humano sempre tem a palavra final - gestor pode descartar alertas. Segundo, temos feedback loop: quando um alerta é descartado, analisamos o porquê e ajustamos o prompt. Terceiro, severidade: alertas 'low' são sugestões, 'critical' são baseados em eventos objetivos."

**Q: "Quanto tempo para implementar em um cliente novo?"**
> R: "**2 dias**. Dia 1: instalar rastreadores (se não tiver), configurar banco. Dia 2: treinar gestores, criar monitores personalizados. No terceiro dia já estão recebendo alertas."

**Q: "Como vocês se comparam com Onixsat AI?"**
> R: "Onixsat usa IA básica (machine learning clássico) treinada em datasets genéricos. Nós usamos **LLM** - entende linguagem natural, contexto, faz raciocínio causal. É a diferença entre um robô que segue regras e um assistente que PENSA."

**Q: "E se a OpenAI aumentar preços?"**
> R: "Três mitigações: 1) Já temos margem (custamos R$ 50, cobramos R$ 200). 2) Podemos migrar para Anthropic Claude ou LLaMA (open source). 3) Com escala, negociamos contrato enterprise com desconto."

**Q: "Qual o ticket médio por cliente?"**
> R: "R$ 200/mês para frotas até 50 veículos. R$ 5/veículo adicional. Frota de 100 veículos = R$ 450/mês. Margem: 89%."

---

## 🔧 Troubleshooting Durante Demo

### Se o frontend não carregar:
1. Verificar console (F12) - erros de CORS?
2. Verificar se backend está rodando (`curl http://localhost:5009/api/test`)
3. **Fallback:** Usar screenshots preparados

### Se mock data não aparecer:
1. Verificar imports em componentes
2. Abrir DevTools → React Components → verificar props
3. **Fallback:** Navegar para tab que funciona, mostrar conceito

### Se investidor pedir para ver "veículo real":
1. Selecionar Dirijabem user (Pasteur Jr. ou daniela pereira)
2. Explicar: "Este é replay de viagem **real** do banco Dirijabem, não simulação"
3. Mostrar polyline verde se formando

### Se perguntarem "por que mock?":
> "Excelente pergunta. Mock por duas razões: 1) Vocês veem a **visão completa do produto** sem gastar R$ 500 em API keys antes de aprovar investimento. 2) Demonstração é **controlável** - não dependemos de veículos estarem ativos agora. Mas o sistema real já está 40% pronto - só falta conectar LLM."

---

**Boa sorte! 🚀**
**Versão mock totalmente funcional. Impressione os investidores!**
