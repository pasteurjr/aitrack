# 🧪 Roteiro de Testes - AITrack + DataDrivr

## ⏱️ Tempo estimado: 10 minutos

---

## ✅ PARTE 1: Verificar Serviços (2 minutos)

### 1.1 Verificar processos rodando

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr

# Deve mostrar 2 processos: socket server + API + simulador
ps aux | grep -E "(run.py|simulator.py)" | grep -v grep
```

**✅ Sucesso se ver:**
- `python3 run.py` (1 processo)
- `python3 simulator.py` (1 processo)

**❌ Se não aparecer, inicie:**
```bash
# Iniciar servidores
nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &

# Iniciar simulador
nohup python3 simulator.py > /tmp/aitrack_simulator.log 2>&1 &

# Aguardar 5 segundos
sleep 5
```

### 1.2 Verificar portas abertas

```bash
ss -tlnp | grep -E ":(9000|5009|3000)"
```

**✅ Sucesso se ver:**
- `9000` - Socket Server
- `5009` - REST API
- `3000` - Frontend React

**❌ Se faltar alguma porta:**
- 9000/5009 faltando: `pkill -f run.py && nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &`
- 3000 faltando: `cd frontend && nohup npm start > /tmp/aitrack_frontend.log 2>&1 &`

### 1.3 Verificar logs em tempo real

```bash
# Abrir em terminal SEPARADO e deixar rodando
tail -f /tmp/aitrack_servers.log
```

**✅ Sucesso se ver linhas assim:**
```
SUCESSO: Posição salva para o veículo FK_VEICOD=1895.
   └─ Behavioral Score: 76.0/100
```

**Isso significa:** GPS sendo recebido e scores calculados! ✅

---

## 🌐 PARTE 2: Testar API (3 minutos)

### 2.1 Testar endpoint de scores

```bash
curl -s http://localhost:5009/api/fleet/scores | python3 -m json.tool
```

**✅ Sucesso se ver JSON com 10 veículos:**
```json
{
    "SIM-1000": 85.0,
    "SIM-1001": 82.0,
    ...
    "SIM-1009": 79.0
}
```

**❌ Se retornar `{}` vazio:**
- Aguardar 10 segundos (simulador envia a cada 5s)
- Verificar se simulator está rodando: `ps aux | grep simulator`

### 2.2 Testar estatísticas da frota

```bash
curl -s http://localhost:5009/api/fleet/stats | python3 -m json.tool
```

**✅ Sucesso se ver:**
```json
{
    "fleet_avg": 81.5,          // Média da frota
    "total_vehicles": 10,        // 10 veículos
    "events_today": 15,          // Eventos detectados hoje
    "top3": [                    // Top 3 motoristas
        {"device_id": "SIM-1000", "score": 85.0},
        ...
    ],
    "bottom3": [                 // Bottom 3 motoristas
        {"device_id": "SIM-1008", "score": 74.0},
        ...
    ]
}
```

**Observar:**
- `events_today` deve ser > 0 (se for 0, aguardar mais tempo)
- `fleet_avg` deve estar entre 70-90
- `top3` e `bottom3` devem ter 3 veículos cada

### 2.3 Testar eventos comportamentais

```bash
curl -s http://localhost:5009/api/fleet/events?limit=5 | python3 -m json.tool
```

**✅ Sucesso se ver eventos como:**
```json
[
    {
        "type": "harsh_brake",
        "device_id": "SIM-1008",
        "severity": "high",
        "icon": "🛑",
        "speed": 45.2,
        "lat": -23.5505,
        "lon": -46.6333,
        "timestamp": "2026-01-27T14:35:22"
    },
    {
        "type": "speeding",
        "icon": "🚨",
        ...
    }
]
```

**Tipos de eventos esperados:**
- `harsh_accel` ⚡
- `harsh_brake` 🛑
- `speeding` 🚨
- `sharp_turn` ↪️

**❌ Se retornar `[]` vazio:**
- Aguardar 30 segundos (eventos são gerados aleatoriamente)
- Motoristas ruins (SIM-1008, SIM-1009) geram mais eventos

### 2.4 Testar score de veículo específico

```bash
curl -s http://localhost:5009/api/vehicles/SIM-1008/score | python3 -m json.tool
```

**✅ Sucesso se ver:**
```json
{
    "device_id": "SIM-1008",
    "score": 74.0
}
```

**Nota:** SIM-1008 e SIM-1009 são os motoristas RUINS (perfil "poor"), então scores devem estar entre 50-75.

---

## 🗺️ PARTE 3: Testar Frontend (5 minutos)

### 3.1 Abrir interface no navegador

```bash
# Abrir automaticamente (se xdg-open disponível)
xdg-open http://localhost:3000

# OU abra manualmente no navegador
# Chrome/Firefox: http://localhost:3000
```

**✅ O que você DEVE ver imediatamente:**

1. **Mapa com região de São Paulo** (-23.55, -46.63)
2. **Dashboard escuro à esquerda** (300px de largura)
3. **Título:** "📊 Fleet Behavioral Dashboard"

**❌ Se aparecer tela branca ou erro:**
```bash
# Ver erros do frontend
tail -30 /tmp/aitrack_frontend.log

# Recompilar se necessário
cd frontend
npm start
```

### 3.2 Verificar marcadores de veículos

**✅ Você deve ver no mapa:**

- **10 marcadores circulares** com números dentro (scores)
- **Cores diferentes:**
  - 🟢 **Verde**: Score 75-100 (motoristas seguros)
  - 🟡 **Amarelo**: Score 50-74 (moderados)
  - 🔴 **Vermelho**: Score 0-49 (alto risco)

**Teste:** Clique em um marcador verde

**✅ Sucesso se popup mostrar:**
```
SIM-1000
Score: 85/100
Status: 🟢 Seguro
Velocidade: 52.3 km/h
```

**Teste:** Clique em um marcador amarelo/vermelho (SIM-1008 ou SIM-1009)

**✅ Sucesso se popup mostrar:**
```
SIM-1008
Score: 74/100
Status: 🟡 Atenção (ou 🔴 Alto Risco se < 50)
Velocidade: 45.2 km/h
```

### 3.3 Verificar ícones de eventos no mapa

**✅ Você deve ver marcadores menores com emojis:**

- ⚡ Aceleração brusca
- 🛑 Frenagem brusca
- 🚨 Excesso de velocidade
- ↪️ Curva brusca

**Teste:** Clique em um ícone de evento

**✅ Sucesso se popup mostrar:**
```
⚡ Aceleração Brusca
Veículo: SIM-1008
Horário: 14:35:22
Severidade: 🔴 Alta
```

**❌ Se não aparecer eventos:**
- Aguardar 30-60 segundos
- Eventos são gerados aleatoriamente pelos motoristas ruins

### 3.4 Verificar Dashboard (lado esquerdo)

**✅ Seção 1: KPI Cards (topo)**

Você deve ver 3 cards com fundo cinza (#374151):

1. **Score Médio**: ~81.5 (colorido: verde se >75, amarelo 50-75)
2. **Eventos Hoje**: número > 0 (aumenta ao longo do tempo)
3. **Veículos**: 10

**Teste:** Observe o "Score Médio" por 10 segundos

**✅ Sucesso se o número mudar** (atualiza a cada 3 segundos)

---

**✅ Seção 2: 🏆 TOP PERFORMERS**

Você deve ver lista com 3 veículos:
```
1. SIM-1000    85.0 (verde)
2. SIM-1006    85.0 (verde)
3. SIM-1001    82.0 (verde)
```

**Teste:** Compare com o mapa - esses veículos devem ter marcadores VERDES

---

**✅ Seção 3: ⚠️ NEEDS ATTENTION (vermelho)**

Você deve ver lista com 3 veículos de menor score:
```
1. SIM-1008    74.0 (amarelo/vermelho)
2. SIM-1009    79.0 (amarelo)
3. SIM-1007    82.0 (verde)
```

**Teste:** Procure SIM-1008 no mapa - deve ter marcador AMARELO ou VERMELHO

---

**✅ Seção 4: 📊 DISTRIBUIÇÃO**

Você deve ver 3 barras horizontais:
```
🟢 Excelente (75+)     ▰▰▰▰▰▰▰▰▰▰ 7
🟡 Moderado (50-74)    ▰▰▰ 2
🔴 Crítico (0-49)      ▱ 1
```

**Teste:** Some os números - deve dar 10 (total de veículos)

### 3.5 Testar atualização em tempo real

**IMPORTANTE:** Dashboard atualiza a cada 3 segundos!

**Teste:**
1. Olhe para o contador "Eventos Hoje"
2. Aguarde 20 segundos
3. O número deve **aumentar**

**✅ Sucesso se:**
- Eventos Hoje: 15 → 17 → 19 (aumenta gradualmente)
- Score Médio pode oscilar: 81.5 → 80.8 → 81.2
- Rankings podem mudar posições

**❌ Se ficar parado (mesmo número após 30s):**
```bash
# Ver se há erro de CORS ou fetch
# Abrir DevTools do navegador (F12)
# Aba "Console" - não deve ter erros vermelhos
# Aba "Network" - deve ver requisições para localhost:5009 a cada 3s
```

---

## 🎭 PARTE 4: Teste de Comportamento (OPCIONAL - 5 minutos)

### 4.1 Identificar motorista ruim

**Objetivo:** Encontrar SIM-1008 ou SIM-1009 e observar eventos

**Passos:**
1. No dashboard, veja "NEEDS ATTENTION"
2. Anote o device_id do último (pior motorista)
3. Procure esse veículo no mapa (marcador amarelo/vermelho)
4. Aguarde 30 segundos observando ao redor dele

**✅ Sucesso se:** Aparecer ícones de eventos (⚡🛑🚨↪️) perto desse veículo

### 4.2 Comparar motorista bom vs ruim

**API Test:**
```bash
# Motorista BOM (perfil "good")
curl -s http://localhost:5009/api/vehicles/SIM-1000/score

# Motorista RUIM (perfil "poor")
curl -s http://localhost:5009/api/vehicles/SIM-1008/score
```

**✅ Sucesso se:**
- SIM-1000: score ~85 (alto)
- SIM-1008: score ~74 (mais baixo)

### 4.3 Observar evolução de score

**Teste longo (2-3 minutos):**

1. Anote o score de SIM-1008 no dashboard
2. Aguarde 2 minutos
3. Verifique novamente

**✅ Sucesso se:**
- Score **diminuiu** (eventos negativos acumulando)
- Exemplo: 74.0 → 71.0 → 68.0

**Nota:** Motoristas ruins têm 25% de chance de evento a cada transmissão (5s), então score cai mais rápido.

---

## 📊 PARTE 5: Checklist Final (1 minuto)

### Antes da Demo, confirme:

- [ ] Mapa exibe 10 veículos com cores diferentes
- [ ] Dashboard mostra "Eventos Hoje" > 0
- [ ] Pelo menos 1 veículo verde (score >75)
- [ ] Pelo menos 1 veículo amarelo/vermelho (score <75)
- [ ] Ícones de eventos visíveis no mapa
- [ ] Dashboard atualiza automaticamente (aguardar 10s)
- [ ] Top 3 performers listados
- [ ] Bottom 3 performers listados
- [ ] Distribuição soma 10 veículos
- [ ] Popup de veículo mostra score e velocidade
- [ ] Popup de evento mostra tipo e severidade

### Se TUDO checado ✅

**🎉 SISTEMA PRONTO PARA DEMO! 🎉**

---

## 🆘 TROUBLESHOOTING RÁPIDO

### Problema: Nenhum veículo no mapa

```bash
# Verificar se simulator está rodando
ps aux | grep simulator.py

# Se não estiver, iniciar
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
nohup python3 simulator.py > /tmp/aitrack_simulator.log 2>&1 &

# Aguardar 15 segundos
sleep 15

# Recarregar página no navegador (F5)
```

### Problema: Dashboard vazio (0 veículos, 0 eventos)

```bash
# Testar API diretamente
curl http://localhost:5009/api/fleet/stats

# Se retornar erro 404 ou conexão recusada:
pkill -f run.py
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &
sleep 10
```

### Problema: Erro CORS no navegador (F12 Console)

```bash
# Reiniciar API com CORS habilitado
pkill -f run.py
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &
```

### Problema: Mapa não carrega (fundo branco)

```bash
# Verificar se Leaflet está instalado
cd frontend
npm list leaflet

# Se não estiver, instalar
npm install leaflet react-leaflet

# Reiniciar frontend
pkill -f "react-scripts start"
npm start
```

### Problema: Scores não mudam (ficam em 85.0 fixo)

**Causa:** Poucos eventos ainda. Motoristas bons mantêm score alto.

**Solução:**
1. Aguardar 2-3 minutos
2. Focar em SIM-1008 e SIM-1009 (motoristas ruins)
3. Esses devem ter score < 80

### Verificação de emergência (30 segundos antes da demo)

```bash
# COMANDO RÁPIDO - testa tudo de uma vez
echo "=== SERVIÇOS ===" && \
ps aux | grep -E "(run.py|simulator)" | grep -v grep && \
echo "" && \
echo "=== PORTAS ===" && \
ss -tlnp | grep -E ":(9000|5009|3000)" && \
echo "" && \
echo "=== API TESTE ===" && \
curl -s http://localhost:5009/api/fleet/stats | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Veículos: {data['total_vehicles']}, Eventos: {data['events_today']}, Média: {data['fleet_avg']}\")"
```

**✅ Saída esperada:**
```
=== SERVIÇOS ===
python3 run.py
python3 simulator.py

=== PORTAS ===
9000 (socket)
5009 (api)
3000 (frontend)

=== API TESTE ===
Veículos: 10, Eventos: 15, Média: 81.5
```

---

## 📞 SUPORTE

Se algo crítico falhar 5 minutos antes da demo:

### RESET COMPLETO (último recurso - 2 minutos)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr

# Matar tudo
pkill -f run.py
pkill -f simulator.py
pkill -f "react-scripts start"

# Aguardar processos fecharem
sleep 3

# Reiniciar na ordem
nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &
sleep 5
nohup python3 simulator.py > /tmp/aitrack_simulator.log 2>&1 &
sleep 5
cd frontend && nohup npm start > /tmp/aitrack_frontend.log 2>&1 &

# Aguardar frontend compilar (30-60 segundos)
sleep 45

# Abrir navegador
xdg-open http://localhost:3000
```

---

## ✅ BOA SORTE NA DEMO! 🚀

**Tempo total de testes:** ~10 minutos
**Última verificação:** 5 minutos antes da apresentação
**URL da demo:** http://localhost:3000
**Horário:** 16:00

**Dica final:** Deixe o dashboard aberto e rodando 5 minutos antes da demo para acumular eventos e ter dados interessantes para mostrar!
