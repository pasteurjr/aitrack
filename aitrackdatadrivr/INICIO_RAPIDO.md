# 🚀 Início Rápido - Testes do Sistema

## 📋 Pré-requisitos

Sistema já está rodando com:
- ✅ API + Socket Server (porta 5009 e 9000)
- ✅ Simulador (10 veículos)
- ⚠️ Frontend precisa ser iniciado manualmente

---

## ⚡ TESTE RÁPIDO (5 minutos)

### 1️⃣ Verificar Status (30 segundos)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr

# Ver status geral
./test.sh status
```

**✅ Você deve ver:**
- Servidores rodando (PID ativo)
- Simulador rodando (PID ativo)
- Veículos: 10
- Eventos: > 0
- Score médio: entre 70-85

---

### 2️⃣ Testar API (1 minuto)

```bash
# Teste completo da API
./test.sh test
```

**✅ Você deve ver:**
- 10 veículos com scores diferentes
- Eventos comportamentais (harsh_brake, speeding, etc.)
- Estatísticas da frota

**OU teste manual:**
```bash
# Ver scores de todos os veículos
curl -s http://localhost:5009/api/fleet/scores | python3 -m json.tool

# Ver estatísticas da frota
curl -s http://localhost:5009/api/fleet/stats | python3 -m json.tool

# Ver últimos 5 eventos
curl -s http://localhost:5009/api/fleet/events?limit=5 | python3 -m json.tool
```

---

### 3️⃣ Abrir Interface (2 minutos)

```bash
# Iniciar frontend (se não estiver rodando)
cd frontend
npm start
# Aguarde ~30 segundos para compilar

# OU use o script
cd ..
./test.sh open
```

**URL:** http://localhost:3000

**✅ Você deve ver:**
- Mapa com 10 marcadores coloridos (🟢🟡🔴)
- Dashboard escuro à esquerda
- Ícones de eventos no mapa (⚡🛑🚨↪️)

---

### 4️⃣ Verificar Atualização em Tempo Real (1 minuto)

No navegador:

1. **Olhe o contador "Eventos Hoje"** no dashboard
2. **Aguarde 10 segundos**
3. O número deve **aumentar** ✅
4. **Scores podem mudar** (observe os marcadores)

---

## 🎯 COMANDOS ÚTEIS

### Ver logs em tempo real

```bash
# Logs do servidor (ver scores sendo calculados)
tail -f /tmp/aitrack_servers.log

# Logs do simulador (ver pacotes sendo enviados)
tail -f /tmp/aitrack_simulator.log
```

### Reiniciar sistema

```bash
# Reiniciar tudo (mantém dados na memória)
./test.sh restart

# Reset completo (limpa scores e eventos)
./test.sh reset
```

### Ver todos os comandos

```bash
./test.sh
```

---

## 📊 O QUE OBSERVAR

### No Mapa

- **Marcadores verdes** 🟢: Motoristas seguros (score 75-100)
- **Marcadores amarelos** 🟡: Atenção moderada (score 50-74)
- **Marcadores vermelhos** 🔴: Alto risco (score 10-49)
- **Ícones de eventos**: ⚡ aceleração, 🛑 frenagem, 🚨 velocidade, ↪️ curva

### No Dashboard

- **Score Médio**: ~77-85 (diminui com eventos negativos)
- **Eventos Hoje**: aumenta constantemente
- **Top 3**: melhores motoristas (verde)
- **Bottom 3**: piores motoristas (precisam coaching)

### Comportamento Esperado

**Motoristas BONS** (SIM-1000 a SIM-1004):
- Scores ficam entre 75-95
- Poucos eventos
- Marcadores verdes

**Motoristas MODERADOS** (SIM-1005 a SIM-1007):
- Scores ficam entre 60-80
- Eventos ocasionais
- Marcadores amarelos/verdes

**Motoristas RUINS** (SIM-1008 a SIM-1009):
- Scores ficam entre 40-70 (caem rápido)
- Eventos frequentes
- Marcadores amarelos/vermelhos

---

## ⚠️ PROBLEMAS COMUNS

### Scores todos em 10 (mínimo)

**Causa:** Simulador rodou muito tempo, scores saturaram

**Solução:**
```bash
./test.sh reset
```

### API não responde

```bash
# Verificar se servidor está rodando
./test.sh check

# Se não estiver, iniciar
./test.sh start
```

### Frontend não abre

```bash
# Iniciar manualmente
cd frontend
npm start

# Aguardar compilação (~30 segundos)
# Abrir http://localhost:3000
```

### Nenhum evento aparece

**Aguarde 1-2 minutos**. Eventos são gerados aleatoriamente:
- Motoristas bons: 5-10% de chance
- Motoristas ruins: 20-25% de chance

---

## 📖 DOCUMENTAÇÃO COMPLETA

Para roteiro detalhado de testes:
```bash
cat ROTEIRO_TESTES.md
```

Para instruções da demo de investidores:
```bash
cat DEMO_INSTRUCTIONS.md
```

---

## ✅ CHECKLIST PRÉ-DEMO

Antes de apresentar, verifique:

```bash
./test.sh full
```

Deve mostrar:
- ✅ Servidores rodando
- ✅ Simulador rodando
- ✅ 10 veículos detectados
- ✅ Eventos > 10
- ✅ Score médio entre 70-85
- ✅ API respondendo

Então:
```bash
./test.sh open
```

**Aguarde 2-3 minutos** para acumular dados interessantes antes de começar a apresentação!

---

## 🎬 COMANDOS DA DEMO

### Preparação (5 minutos antes)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr

# Verificar tudo
./test.sh full

# Abrir interface
./test.sh open

# Deixar acumular dados (2-3 minutos)
```

### Durante a Demo

**Mostrar API ao vivo:**
```bash
# Em terminal separado
curl -s http://localhost:5009/api/fleet/stats | python3 -m json.tool
```

**Mostrar logs em tempo real:**
```bash
# Em terminal separado
tail -f /tmp/aitrack_servers.log | grep "Behavioral Score"
```

### Após a Demo

```bash
# Parar tudo (economizar recursos)
./test.sh stop
```

---

## 📞 AJUDA RÁPIDA

**Sistema travado?**
```bash
./test.sh restart
```

**Dados muito antigos?**
```bash
./test.sh reset
```

**Ver o que está acontecendo?**
```bash
./test.sh status
tail -f /tmp/aitrack_servers.log
```

**Tudo está quebrado! (PÂNICO)**
```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
./test.sh stop
sleep 5
./test.sh start
sleep 15
./test.sh open
```

---

## 🏁 BOA SORTE!

Sistema está **100% funcional** e pronto para testes/demo.

**Próximos passos:**
1. `./test.sh status` - Verificar status
2. `./test.sh open` - Abrir interface
3. Aguardar 2-3 minutos para dados acumularem
4. Começar apresentação!

**Dúvidas?** Consulte `ROTEIRO_TESTES.md` ou `DEMO_INSTRUCTIONS.md`
