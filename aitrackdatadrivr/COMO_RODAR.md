# Como Rodar o Sistema AITrack + DataDrivr + Dirijabem

## Arquitetura do Sistema

O sistema possui 3 componentes backend e 1 frontend:

### Backend (run.py inicia tudo junto)
1. **Socket Server** - Porta 9000 - Recebe dados dos trackers TRACKER
2. **API Flask** - Porta 5009 - API REST para frontend
3. **Simulador Dirijabem** - Gerencia replays de viagens reais

### Frontend
4. **React App** - Porta 3000 - Interface web com mapa

---

## 🚀 Início Rápido

### 1. Backend (Terminal 1)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
python run.py
```

Você verá:
```
Iniciando todos os serviços AITrack + Dirijabem...
Iniciando o Servidor de Socket AITrack...
Iniciando o Servidor da API Flask em http://0.0.0.0:5009...
Iniciando o Simulador Dirijabem...
[DIRIJABEM] Starting replay loop
[DIRIJABEM] Replay manager started
Simulador Dirijabem pronto e aguardando requisições...
```

### 2. Simulador TRACKER (Terminal 2 - Opcional)

Para gerar dados dos veículos TRACKER simulados:

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr
python simulator.py
```

Isso cria 10 veículos simulados (SIM-1000 a SIM-1009) que enviam posições para o socket server.

Para uma prova determinística, use o executor de cenários. Ele valida cada pacote
no parser antes do envio e nunca fabrica pânico, tamper ou comando físico:

```bash
# Validar sem gravar
python tracker_scenario_simulator.py external-power-loss \
  --protocol suntech --device-id SIM-1000 --time-scale 0 --dry-run

# Enviar pelo socket real (porta 9000)
python tracker_scenario_simulator.py normal \
  --protocol suntech --device-id SIM-1000 --time-scale 0
```

Cenários: `normal`, `ignition-cycle`, `external-power-loss`, `gps-invalid`
(somente Maxtrack) e `offline-silence`. O `--time-scale 0` remove esperas para
testes; use `1` para respeitar os intervalos descritos pelo cenário.

### 3. Frontend (Terminal 3)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr/frontend
npm start
```

Abre automaticamente em http://localhost:3000

---

## 📱 Como Usar

### Interface Web

A interface possui:

**Barra Lateral Esquerda:**
- **Dashboard**: Mostra scores da frota, top performers, distribuição
  - Select "🚗 TRACKER": Escolha veículo simulado (SIM-1000 a SIM-1009)
  - Select "🏁 DIRIJABEM": Escolha usuário real (Pasteur Jr., daniela pereira, etc.)
- **Timeline**: Eventos comportamentais (frenadas, acelerações bruscas)
- **Análises**: Gráficos e estatísticas

**Mapa (Centro):**
- Mostra veículos em tempo real
- **Polyline Vermelha**: Trilha do veículo TRACKER selecionado
- **Polyline Verde**: Trilha da viagem DIRIJABEM selecionada
- Ambos podem estar ativos simultaneamente!

---

## 🎮 Cenários de Uso

### Cenário 1: Ver Frota TRACKER
1. Rode `python run.py`
2. Rode `python simulator.py`
3. Abra frontend
4. Selecione veículo no dropdown "🚗 TRACKER"
5. Veja polyline vermelha no mapa

### Cenário 2: Replay de Viagem Real (Dirijabem)
1. Rode `python run.py`
2. Abra frontend
3. Selecione usuário no dropdown "🏁 DIRIJABEM"
4. Veja polyline verde aparecendo gradualmente (replay em tempo real)
5. Quando a viagem terminar, você pode selecionar novamente para nova viagem

### Cenário 3: Ambos Simultaneamente
1. Rode `python run.py` + `python simulator.py`
2. Abra frontend
3. Selecione veículo TRACKER → polyline vermelha
4. Selecione usuário DIRIJABEM → polyline verde
5. Ambos aparecem no mapa juntos!

---

## ⚙️ Configurações

### SPEED_MULTIPLIER (Velocidade do Replay)

Edite `dirijabem_simulator.py`:

```python
SPEED_MULTIPLIER = 1   # Tempo real (padrão)
SPEED_MULTIPLIER = 10  # 10x mais rápido
SPEED_MULTIPLIER = 100 # 100x mais rápido
```

Reinicie `run.py` após mudar.

---

## 🗄️ Bancos de Dados

### Banco TRACKER (Veículos Simulados)
- Host: camerascasas.no-ip.info:3307
- Database: tracker
- Tabelas: veiculos, localizacao

### Banco DIRIJABEM (Viagens Reais)
- Host: camerascasas.no-ip.info:3307
- Database: dirijabem
- Tabelas: viagem, localizacaodados, usuario

---

## 🐛 Troubleshooting

### "Routes file not found"
Execute a extração de rotas primeiro:
```bash
python extract_dirijabem_routes.py
```

### Frontend não conecta
Verifique se a API está rodando:
```bash
curl http://localhost:5009/api/test
```

### Nenhum veículo aparece
Rode o simulador TRACKER:
```bash
python simulator.py
```

### Viagem Dirijabem não começa
Verifique logs no terminal onde rodou `run.py`:
```
[DIRIJABEM] Starting new trip for Pasteur Jr. (route 2598 → CODVIA=12345)
```

---

## 📊 Endpoints da API

### TRACKER
- `GET /api/posicoes` - Veículos online
- `GET /api/positions/history/<veicod>` - Histórico
- `GET /api/positions/latest/<veicod>` - Última posição

### DIRIJABEM
- `GET /api/dirijabem/users` - Lista usuários
- `POST /api/dirijabem/user/<codusu>/start` - Iniciar/retomar viagem
- `POST /api/dirijabem/user/<codusu>/stop` - Parar viagem
- `GET /api/dirijabem/user/<codusu>/route` - Rota completa
- `GET /api/dirijabem/user/<codusu>/position` - Posição atual
- `GET /api/dirijabem/user/<codusu>/status` - Status da viagem

### BEHAVIORAL
- `GET /api/fleet/scores` - Scores de todos veículos
- `GET /api/fleet/events` - Eventos comportamentais
- `GET /api/fleet/stats` - Estatísticas da frota

---

## 📝 Notas Importantes

1. **Trip State Management**:
   - Se uma viagem Dirijabem for interrompida (parar o backend), ao reiniciar e selecionar o mesmo usuário, ela **retoma do último ponto**.
   - Para nova viagem, espere a atual terminar ou delete a viagem no banco.

2. **Diferenças TRACKER vs DIRIJABEM**:
   - TRACKER: Loop infinito, dados sintéticos
   - DIRIJABEM: Viagens finitas, dados reais com métricas copiadas

3. **Métricas Comportamentais**:
   - OST, OSA, GAA, OSP: Over-speeding
   - SAM, SAA: Sudden acceleration
   - BRP, BRM, BRA: Braking
   - GAP, GAN, GAM: G-force/cornering
   - SCORE: Overall fuzzy logic score

4. **100 Rotas Pré-extraídas**:
   - 10 usuários × 10 rotas cada
   - Total: 158,668 pontos GPS
   - Arquivo: `config/dirijabem_routes.json` (23.8 MB)

---

## 🎯 Próximos Passos

- [ ] Implementar cálculo de métricas em tempo real (OST, OSA, etc.)
- [ ] WebSocket para updates em tempo real (substituir polling)
- [ ] Controles de playback (pause, fast-forward, rewind)
- [ ] Dashboard de viagens ativas
- [ ] Comparação lado a lado de 2 viagens

---

**Sistema pronto para uso! 🚀**
