#!/bin/bash
# Script de testes rápidos - AITrack + DataDrivr
# Uso: ./test.sh [comando]

cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Função: Verificar serviços
function check_services() {
    print_header "VERIFICANDO SERVIÇOS"

    if ps aux | grep "run.py" | grep -v grep > /dev/null; then
        print_success "Servidores (API + Socket) rodando"
    else
        print_error "Servidores NÃO estão rodando"
        echo "Execute: ./test.sh start"
        return 1
    fi

    if ps aux | grep "simulator.py" | grep -v grep > /dev/null; then
        print_success "Simulador rodando"
    else
        print_error "Simulador NÃO está rodando"
        echo "Execute: ./test.sh start"
        return 1
    fi

    echo ""
    print_header "VERIFICANDO PORTAS"

    if ss -tlnp 2>/dev/null | grep ":9000" > /dev/null; then
        print_success "Porta 9000 (Socket Server) aberta"
    else
        print_error "Porta 9000 fechada"
    fi

    if ss -tlnp 2>/dev/null | grep ":5009" > /dev/null; then
        print_success "Porta 5009 (REST API) aberta"
    else
        print_error "Porta 5009 fechada"
    fi

    if ss -tlnp 2>/dev/null | grep ":3000" > /dev/null; then
        print_success "Porta 3000 (Frontend) aberta"
    else
        print_warning "Porta 3000 fechada (frontend não iniciado)"
        echo "Execute: cd frontend && npm start"
    fi
}

# Função: Testar API
function test_api() {
    print_header "TESTANDO API"

    echo "1. Testando /api/fleet/scores..."
    SCORES=$(curl -s http://localhost:5009/api/fleet/scores)
    if echo "$SCORES" | grep -q "SIM-"; then
        VEHICLE_COUNT=$(echo "$SCORES" | grep -o "SIM-" | wc -l)
        print_success "API respondendo - $VEHICLE_COUNT veículos detectados"
        echo "$SCORES" | python3 -m json.tool | head -15
    else
        print_error "API não retornou veículos"
        echo "Resposta: $SCORES"
    fi

    echo ""
    echo "2. Testando /api/fleet/stats..."
    STATS=$(curl -s http://localhost:5009/api/fleet/stats)
    if echo "$STATS" | grep -q "fleet_avg"; then
        print_success "Estatísticas da frota disponíveis"
        echo "$STATS" | python3 -m json.tool
    else
        print_error "Estatísticas não disponíveis"
    fi

    echo ""
    echo "3. Testando /api/fleet/events..."
    EVENTS=$(curl -s http://localhost:5009/api/fleet/events?limit=3)
    EVENT_COUNT=$(echo "$EVENTS" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
    if [ "$EVENT_COUNT" -gt 0 ] 2>/dev/null; then
        print_success "$EVENT_COUNT eventos detectados"
        echo "$EVENTS" | python3 -m json.tool | head -30
    else
        print_warning "Nenhum evento ainda (aguarde 30-60 segundos)"
    fi
}

# Função: Status resumido
function status() {
    print_header "STATUS DO SISTEMA"

    # Serviços
    RUN_PID=$(pgrep -f "run.py" | head -1)
    SIM_PID=$(pgrep -f "simulator.py" | head -1)
    FRONT_PID=$(pgrep -f "react-scripts start" | head -1)

    echo "Servidores (run.py):  ${RUN_PID:-❌ não rodando}"
    echo "Simulador:            ${SIM_PID:-❌ não rodando}"
    echo "Frontend:             ${FRONT_PID:-❌ não rodando}"

    echo ""

    # Teste rápido da API
    if [ -n "$RUN_PID" ]; then
        STATS=$(curl -s http://localhost:5009/api/fleet/stats 2>/dev/null)
        if [ -n "$STATS" ]; then
            VEHICLES=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_vehicles', 0))" 2>/dev/null)
            EVENTS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('events_today', 0))" 2>/dev/null)
            AVG=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('fleet_avg', 0))" 2>/dev/null)

            echo "Veículos monitorados: $VEHICLES"
            echo "Eventos hoje:         $EVENTS"
            echo "Score médio:          $AVG"
        fi
    fi

    echo ""
    echo "Frontend: http://localhost:3000"
}

# Função: Iniciar todos os serviços
function start_all() {
    print_header "INICIANDO TODOS OS SERVIÇOS"

    # Verificar se já está rodando
    if ps aux | grep "run.py" | grep -v grep > /dev/null; then
        print_warning "Servidores já estão rodando"
    else
        echo "Iniciando servidores (API + Socket)..."
        nohup python3 run.py > /tmp/aitrack_servers.log 2>&1 &
        sleep 3
        print_success "Servidores iniciados (PID: $(pgrep -f run.py))"
    fi

    if ps aux | grep "simulator.py" | grep -v grep > /dev/null; then
        print_warning "Simulador já está rodando"
    else
        echo "Iniciando simulador..."
        nohup python3 simulator.py > /tmp/aitrack_simulator.log 2>&1 &
        sleep 2
        print_success "Simulador iniciado (PID: $(pgrep -f simulator.py))"
    fi

    echo ""
    print_success "Aguarde 10 segundos para dados aparecerem..."
    sleep 10

    # Teste rápido
    test_api
}

# Função: Parar todos os serviços
function stop_all() {
    print_header "PARANDO TODOS OS SERVIÇOS"

    pkill -f "run.py" 2>/dev/null && print_success "Servidores parados" || print_warning "Servidores já estavam parados"
    pkill -f "simulator.py" 2>/dev/null && print_success "Simulador parado" || print_warning "Simulador já estava parado"
    pkill -f "react-scripts start" 2>/dev/null && print_success "Frontend parado" || print_warning "Frontend já estava parado"

    sleep 2
    print_success "Todos os serviços foram parados"
}

# Função: Reiniciar tudo
function restart_all() {
    stop_all
    echo ""
    sleep 2
    start_all
}

# Função: Ver logs
function logs() {
    SERVICE=$1

    if [ "$SERVICE" == "server" ] || [ "$SERVICE" == "api" ]; then
        tail -30 /tmp/aitrack_servers.log
    elif [ "$SERVICE" == "simulator" ] || [ "$SERVICE" == "sim" ]; then
        tail -30 /tmp/aitrack_simulator.log
    elif [ "$SERVICE" == "frontend" ] || [ "$SERVICE" == "front" ]; then
        tail -30 /tmp/aitrack_frontend.log
    else
        echo "Logs disponíveis:"
        echo "  ./test.sh logs server     - Logs do servidor (API + Socket)"
        echo "  ./test.sh logs simulator  - Logs do simulador"
        echo "  ./test.sh logs frontend   - Logs do frontend"
    fi
}

# Função: Verificação completa
function full_check() {
    check_services
    echo ""
    test_api
    echo ""
    status

    echo ""
    print_header "VERIFICAÇÃO COMPLETA"
    print_success "Se tudo acima está OK, o sistema está pronto!"
    echo ""
    echo "Abrir frontend: xdg-open http://localhost:3000"
}

# Função: Abrir navegador
function open_browser() {
    print_header "ABRINDO INTERFACE"

    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:3000
        print_success "Navegador aberto em http://localhost:3000"
    elif command -v open > /dev/null; then
        open http://localhost:3000
        print_success "Navegador aberto em http://localhost:3000"
    else
        print_warning "Não foi possível abrir automaticamente"
        echo "Abra manualmente: http://localhost:3000"
    fi
}

# Função: Reset completo (scores zerados, eventos limpos)
function reset_scores() {
    print_header "RESET COMPLETO DO SISTEMA"

    echo "Isso vai:"
    echo "  - Parar todos os serviços"
    echo "  - Limpar scores e eventos da memória"
    echo "  - Reiniciar com dados frescos"
    echo ""
    read -p "Confirma reset? (s/N) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_warning "Reset cancelado"
        return
    fi

    # Parar tudo
    stop_all
    sleep 3

    # Limpar logs
    > /tmp/aitrack_servers.log
    > /tmp/aitrack_simulator.log

    print_success "Logs limpos"
    sleep 1

    # Reiniciar
    start_all

    print_success "Sistema resetado com scores iniciais (85.0)"
}

# Menu principal
case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status
        ;;
    check)
        check_services
        ;;
    test)
        test_api
        ;;
    full)
        full_check
        ;;
    logs)
        logs "$2"
        ;;
    open)
        open_browser
        ;;
    reset)
        reset_scores
        ;;
    *)
        echo "AITrack + DataDrivr - Script de Testes"
        echo ""
        echo "Uso: ./test.sh [comando]"
        echo ""
        echo "Comandos disponíveis:"
        echo "  start      - Inicia todos os serviços (API, Socket, Simulador)"
        echo "  stop       - Para todos os serviços"
        echo "  restart    - Reinicia todos os serviços"
        echo "  reset      - Reset completo (limpa scores e eventos)"
        echo "  status     - Mostra status resumido do sistema"
        echo "  check      - Verifica se serviços estão rodando"
        echo "  test       - Testa endpoints da API"
        echo "  full       - Verificação completa (check + test + status)"
        echo "  logs [tipo]- Mostra logs (server|simulator|frontend)"
        echo "  open       - Abre interface no navegador"
        echo ""
        echo "Exemplos:"
        echo "  ./test.sh start       # Inicia tudo"
        echo "  ./test.sh reset       # Limpar dados e reiniciar"
        echo "  ./test.sh full        # Verifica tudo"
        echo "  ./test.sh logs server # Ver logs do servidor"
        echo "  ./test.sh open        # Abrir http://localhost:3000"
        echo ""
        echo "Para roteiro completo: cat ROTEIRO_TESTES.md"
        ;;
esac
