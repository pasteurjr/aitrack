"""
Monitor Engine - AI Monitor Scheduler
Analyzes vehicles in active monitors and generates alerts
Simplified version without LLM (rule-based analysis)
"""

import time
import schedule
from datetime import datetime, timedelta
from . import monitor_db
from .behavioral_engine import get_vehicle_score, get_recent_events


def analyze_monitor(monitor_id: int):
    """
    Analisa veículos de um monitor usando regras simples (SEM LLM)

    Args:
        monitor_id: ID do monitor a ser analisado
    """
    try:
        monitor = monitor_db.get_monitor_by_id(monitor_id)
        if not monitor or not monitor['ativo']:
            return

        vehicles = monitor_db.get_monitor_vehicles(monitor_id)

        print(f"[MONITOR #{monitor_id}] Analisando {len(vehicles)} veículos...")

        for vehicle in vehicles:
            device_id = vehicle['device_id']
            score = get_vehicle_score(device_id)

            # Verificar threshold - só analisa se score está abaixo
            if score >= monitor['score_threshold']:
                continue  # Score OK, skip

            # Pegar eventos na janela de contexto
            janela_segundos = monitor['janela_contexto']
            tempo_inicio = datetime.now() - timedelta(seconds=janela_segundos)

            all_events = get_recent_events(limit=1000, device_id=device_id)
            events_janela = [e for e in all_events if
                            datetime.fromisoformat(e['timestamp']) > tempo_inicio]

            # Verificar quantidade mínima de eventos
            if len(events_janela) < monitor['eventos_minimos']:
                continue  # Poucos eventos, skip

            # Análise simples baseada em regras (sem LLM)
            severity = 'medium'
            if score < 50:
                severity = 'critical'
            elif score < 60:
                severity = 'high'

            # Contar eventos por tipo
            eventos_por_tipo = {}
            for event in events_janela:
                tipo = event['type']
                eventos_por_tipo[tipo] = eventos_por_tipo.get(tipo, 0) + 1

            conclusao = f"Score {score:.1f} - {len(events_janela)} eventos em {janela_segundos//60} min"

            # Adicionar detalhes dos eventos mais frequentes
            if eventos_por_tipo:
                top_eventos = sorted(eventos_por_tipo.items(), key=lambda x: x[1], reverse=True)[:3]
                conclusao += f". Mais frequentes: {', '.join(f'{tipo} ({count})' for tipo, count in top_eventos)}"

            # Salvar análise
            analysis_data = {
                'veiculomonitor_id': vehicle['id'],
                'periodo_inicio': tempo_inicio,
                'periodo_fim': datetime.now(),
                'total_eventos': len(events_janela),
                'score_inicial': min(100, score + 5),  # Aproximação
                'score_final': score,
                'eventos_por_tipo': eventos_por_tipo,
                'conclusao': conclusao,
                'severidade': severity
            }

            analysis_id = monitor_db.save_analysis(monitor_id, vehicle['id'], analysis_data)

            # Gerar alerta se configurado e severidade alta o suficiente
            if monitor['gera_alertas'] and severity in ['high', 'critical']:
                alert_data = {
                    'analise_id': analysis_id,
                    'monitor_id': monitor_id,
                    'veiculomonitor_id': vehicle['id'],
                    'device_id': device_id,
                    'nome_motorista': vehicle.get('nome_motorista'),
                    'titulo': f"Score baixo detectado: {score:.1f} ({device_id})",
                    'mensagem': f"Veículo {device_id} apresentou score de {score:.1f} com {len(events_janela)} eventos em {janela_segundos//60} minutos. {conclusao}",
                    'severidade': severity,
                    'tipo': monitor['tipo_monitor'],
                    'total_eventos_relacionados': len(events_janela)
                }

                alert_id = monitor_db.create_alert(alert_data)
                print(f"[ALERT #{alert_id}] Criado para {device_id} (score: {score:.1f}, severity: {severity})")

    except Exception as e:
        print(f"[ERROR] Erro analisando monitor #{monitor_id}: {e}")


def schedule_monitors():
    """
    Agenda monitores ativos para análise periódica
    """
    try:
        monitors = monitor_db.get_active_monitors()

        print(f"[MONITOR ENGINE] Agendando {len(monitors)} monitores ativos...")

        for monitor in monitors:
            interval_min = monitor['intervalo_analise'] // 60

            # Agenda análise periódica
            schedule.every(interval_min).minutes.do(analyze_monitor, monitor['id'])

            print(f"[MONITOR ENGINE] Monitor #{monitor['id']} agendado a cada {interval_min} min")

        print(f"[MONITOR ENGINE] Todos os monitores agendados com sucesso!")

    except Exception as e:
        print(f"[ERROR] Erro agendando monitores: {e}")


def run():
    """
    Loop principal do monitor engine
    """
    print("[MONITOR ENGINE] Iniciando Monitor Engine...")
    print("[MONITOR ENGINE] Versão simplificada (sem LLM)")

    # Agenda monitores na inicialização
    schedule_monitors()

    # Loop infinito verificando o scheduler
    print("[MONITOR ENGINE] Entrando em loop de monitoramento...")

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("[MONITOR ENGINE] Parando Monitor Engine...")
            break
        except Exception as e:
            print(f"[ERROR] Erro no loop principal: {e}")
            time.sleep(5)  # Espera 5 segundos antes de tentar novamente


if __name__ == '__main__':
    run()
