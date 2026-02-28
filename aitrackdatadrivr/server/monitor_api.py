"""
Flask Blueprint for AI Monitor API endpoints
Provides REST API for monitors, vehicles, analyses, and alerts
"""

from flask import Blueprint, request, jsonify
from . import monitor_db

monitor_bp = Blueprint('monitor', __name__)


# ==================== Monitores ====================

@monitor_bp.route('/api/monitors', methods=['GET'])
def get_monitors():
    """Lista todos os monitores"""
    try:
        monitors = monitor_db.get_all_monitors()
        return jsonify(monitors)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors/<int:monitor_id>', methods=['GET'])
def get_monitor(monitor_id):
    """Retorna detalhes de um monitor"""
    try:
        monitor = monitor_db.get_monitor_by_id(monitor_id)
        if not monitor:
            return jsonify({'error': 'Monitor not found'}), 404
        return jsonify(monitor)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors', methods=['POST'])
def create_monitor():
    """Cria novo monitor"""
    try:
        data = request.json
        monitor_id = monitor_db.create_monitor(data)
        return jsonify({'id': monitor_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors/<int:monitor_id>', methods=['PUT'])
def update_monitor(monitor_id):
    """Atualiza monitor"""
    try:
        data = request.json
        success = monitor_db.update_monitor(monitor_id, data)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Monitor not found or no changes made'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors/<int:monitor_id>/toggle', methods=['POST'])
def toggle_monitor(monitor_id):
    """Ativa/desativa monitor"""
    try:
        data = request.json
        ativo = data.get('ativo', True)
        success = monitor_db.toggle_monitor(monitor_id, ativo)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Monitor not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Veículos em Monitores ====================

@monitor_bp.route('/api/monitors/<int:monitor_id>/vehicles', methods=['GET'])
def get_monitor_vehicles(monitor_id):
    """Lista veículos de um monitor"""
    try:
        vehicles = monitor_db.get_monitor_vehicles(monitor_id)

        # Enriquecer com status do behavioral_engine
        try:
            from behavioral_engine import get_vehicle_score, get_recent_events
            from datetime import datetime, timedelta

            # Get events from today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            for vehicle in vehicles:
                device_id = vehicle['device_id']

                # Get score
                vehicle['score_atual'] = get_vehicle_score(device_id)

                # Count events today
                all_events = get_recent_events(limit=1000, device_id=device_id)
                events_today = [e for e in all_events if
                               datetime.fromisoformat(e['timestamp']) >= today_start]
                vehicle['total_eventos_hoje'] = len(events_today)

                # Determine status based on score
                score = vehicle['score_atual']
                if score >= 70:
                    vehicle['status'] = 'ok'
                elif score >= 55:
                    vehicle['status'] = 'warning'
                else:
                    vehicle['status'] = 'critical'

        except ImportError:
            # Behavioral engine not available, use defaults
            for vehicle in vehicles:
                vehicle['score_atual'] = 85.0
                vehicle['total_eventos_hoje'] = 0
                vehicle['status'] = 'ok'

        return jsonify(vehicles)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors/<int:monitor_id>/vehicles', methods=['POST'])
def add_vehicle_to_monitor(monitor_id):
    """Adiciona veículo ao monitor"""
    try:
        data = request.json
        veicod = data.get('veicod')
        device_id = data.get('device_id')

        if not veicod or not device_id:
            return jsonify({'error': 'veicod and device_id are required'}), 400

        veiculomonitor_id = monitor_db.add_vehicle_to_monitor(monitor_id, veicod, device_id)
        return jsonify({'id': veiculomonitor_id, 'success': True}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/monitors/vehicles/<int:veiculomonitor_id>', methods=['DELETE'])
def remove_vehicle_from_monitor(veiculomonitor_id):
    """Remove veículo do monitor"""
    try:
        success = monitor_db.remove_vehicle_from_monitor(veiculomonitor_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Vehicle not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Análises ====================

@monitor_bp.route('/api/monitors/<int:monitor_id>/analyses', methods=['GET'])
def get_analyses(monitor_id):
    """Lista análises de um monitor"""
    try:
        limit = request.args.get('limit', 50, type=int)
        analyses = monitor_db.get_monitor_analyses(monitor_id, limit)
        return jsonify(analyses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Alertas ====================

@monitor_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Lista alertas com filtros"""
    try:
        status = request.args.get('status')
        severidade = request.args.get('severidade')
        monitor_id = request.args.get('monitor_id', type=int)

        filters = {}
        if status:
            filters['status'] = status
        if severidade:
            filters['severidade'] = severidade
        if monitor_id:
            filters['monitor_id'] = monitor_id

        alerts = monitor_db.get_alerts(filters)
        return jsonify(alerts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/alerts/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Retorna detalhes de um alerta"""
    try:
        alert = monitor_db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        return jsonify(alert)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/alerts/<int:alert_id>/acknowledge', methods=['PUT'])
def acknowledge_alert(alert_id):
    """Reconhece alerta"""
    try:
        data = request.json
        reconhecido_por = data.get('reconhecido_por', 'Unknown')
        success = monitor_db.acknowledge_alert(alert_id, reconhecido_por)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Resolve alerta"""
    try:
        success = monitor_db.resolve_alert(alert_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/alerts/<int:alert_id>/dismiss', methods=['PUT'])
def dismiss_alert(alert_id):
    """Descarta alerta"""
    try:
        success = monitor_db.dismiss_alert(alert_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Estatísticas ====================

@monitor_bp.route('/api/monitors/stats', methods=['GET'])
def get_monitor_stats():
    """Estatísticas gerais dos monitores"""
    try:
        stats = monitor_db.get_monitor_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/alerts/stats', methods=['GET'])
def get_alert_stats():
    """Estatísticas de alertas"""
    try:
        stats = monitor_db.get_alert_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Catálogo de Eventos ====================

@monitor_bp.route('/api/events/catalog', methods=['GET'])
def get_events_catalog():
    """Retorna catálogo de tipos de eventos"""
    try:
        conn = monitor_db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tipo_evento ORDER BY categoria, nome")
        catalog = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(catalog)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@monitor_bp.route('/api/events/stats', methods=['GET'])
def get_events_stats():
    """Retorna estatísticas de eventos"""
    try:
        # Try to get from behavioral_engine (in-memory)
        try:
            from behavioral_engine import get_recent_events
            events = get_recent_events(limit=1000)

            stats = {
                'total_eventos_hoje': len(events),
                'por_tipo': {},
                'por_categoria': {}
            }

            # Group by type
            for event in events:
                tipo = event['type']
                stats['por_tipo'][tipo] = stats['por_tipo'].get(tipo, 0) + 1

            return jsonify(stats)
        except ImportError:
            # Fall back to database query
            conn = monitor_db.get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT te.codigo, te.nome, te.categoria, COUNT(*) as count
                FROM eventos e
                JOIN tipo_evento te ON e.tipo_evento_id = te.id
                WHERE DATE(e.timestamp) = CURDATE()
                GROUP BY te.codigo, te.nome, te.categoria
            """)

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            stats = {
                'total_eventos_hoje': sum(r['count'] for r in results),
                'por_tipo': {r['codigo']: r['count'] for r in results},
                'por_categoria': {}
            }

            # Group by category
            for r in results:
                cat = r['categoria']
                stats['por_categoria'][cat] = stats['por_categoria'].get(cat, 0) + r['count']

            return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Eventos (histórico) ====================

@monitor_bp.route('/api/events', methods=['GET'])
def get_events():
    """Lista eventos do banco com filtros"""
    try:
        limit = request.args.get('limit', 100, type=int)
        device_id = request.args.get('device_id')
        categoria = request.args.get('categoria')

        conn = monitor_db.get_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT e.id, te.codigo as tipo_evento_codigo, te.nome as tipo_evento_nome,
               te.categoria, e.severidade, e.device_id, e.timestamp,
               e.latitude, e.longitude, e.velocidade, e.dados_adicionais
        FROM eventos e
        JOIN tipo_evento te ON e.tipo_evento_id = te.id
        WHERE 1=1
        """

        params = []

        if device_id:
            sql += " AND e.device_id = %s"
            params.append(device_id)

        if categoria:
            sql += " AND te.categoria = %s"
            params.append(categoria)

        sql += " ORDER BY e.timestamp DESC LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        events = cursor.fetchall()

        # Convert timestamp to ISO
        for event in events:
            if event['timestamp']:
                event['timestamp'] = event['timestamp'].isoformat()
            if event['dados_adicionais']:
                import json
                event['dados_adicionais'] = json.loads(event['dados_adicionais'])

        cursor.close()
        conn.close()

        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
