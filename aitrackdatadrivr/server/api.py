import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import datetime
from .env_loader import load_dotenv

# carrega .env (config/.env ou .env)
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('AITRACK_DB_HOST', 'camerascasas.no-ip.info'),
    'port': int(os.getenv('AITRACK_DB_PORT', '3307')),
    'user': os.getenv('AITRACK_DB_USER', 'scadabr'),
    'password': os.getenv('AITRACK_DB_PASSWORD', 'scadabr'),
    'database': os.getenv('AITRACK_DB_NAME', 'tracker'),
}

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Função helper para converter datetimes para o formato ISO
def format_results(results):
    for row in results:
        if 'DATAHORA' in row and isinstance(row['DATAHORA'], datetime.datetime):
            row['DATAHORA'] = row['DATAHORA'].isoformat()
    return results

@app.route('/api/posicoes', methods=['GET'])
def get_latest_positions():
    """Busca veículos que transmitiram nos últimos 10 minutos (ONLINE) com posições."""
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                    SELECT
                        v.VEICOD,
                        v.VEIPLACA,
                        v.VEI_DEVICE_ID,
                        ST_Y(l.LOCLATLONG) as latitude,
                        ST_X(l.LOCLATLONG) as longitude,
                        l.VELATU as velocidade_kmh,
                        l.DATAHORA
                    FROM
                        localizacao l
                    INNER JOIN (
                        SELECT FK_VEICOD, MAX(DATAHORA) as max_datahora
                        FROM localizacao
                        GROUP BY FK_VEICOD
                    ) AS latest ON l.FK_VEICOD = latest.FK_VEICOD AND l.DATAHORA = latest.max_datahora
                    JOIN
                        veiculos v ON l.FK_VEICOD = v.VEICOD
                    WHERE
                        l.DATAHORA >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
                    ORDER BY
                        v.VEICOD ASC;
                """
                cursor.execute(query)
                positions = cursor.fetchall()
                return jsonify(format_results(positions))
    except mysql.connector.Error as err:
        return jsonify({"erro": f"Erro de banco de dados: {err}"}), 500

@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({"message": "A rota de teste funcionou!"})

@app.route('/api/positions/history/<int:vehicle_id>', methods=['GET'])
def get_position_history(vehicle_id):
    """Busca todo o histórico de posições para um veículo específico."""
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                # Suporte a limite opcional de pontos mais recentes (default 100)
                try:
                    limit = int(request.args.get('limit', '100'))
                    limit = max(1, min(limit, 1000))
                except ValueError:
                    limit = 100

                # Busca últimos N pontos em ordem cronológica ASC
                query = f"""
                    SELECT latitude, longitude, DATAHORA, velocidade_kmh FROM (
                        SELECT 
                            ST_Y(LOCLATLONG) as latitude, 
                            ST_X(LOCLATLONG) as longitude,
                            DATAHORA, 
                            VELATU as velocidade_kmh
                        FROM 
                            localizacao
                        WHERE FK_VEICOD = %s
                        ORDER BY DATAHORA DESC
                        LIMIT {limit}
                    ) t
                    ORDER BY DATAHORA ASC;
                """
                cursor.execute(query, (vehicle_id,))
                history = cursor.fetchall()
                return jsonify(format_results(history))
    except mysql.connector.Error as err:
        return jsonify({"erro": f"Erro de banco de dados: {err}"}), 500

@app.route('/api/positions/latest/<int:vehicle_id>', methods=['GET'])
def get_latest_for_vehicle(vehicle_id):
    """Busca a última posição para um veículo específico."""
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                    SELECT 
                        ST_Y(LOCLATLONG) as latitude, 
                        ST_X(LOCLATLONG) as longitude,
                        DATAHORA, 
                        VELATU as velocidade_kmh
                    FROM 
                        localizacao
                    WHERE FK_VEICOD = %s
                    ORDER BY DATAHORA DESC
                    LIMIT 1;
                """
                cursor.execute(query, (vehicle_id,))
                latest = cursor.fetchone()
                if latest:
                    # A função format_results espera uma lista
                    return jsonify(format_results([latest])[0])
                return jsonify(None) # Retorna nulo se não houver histórico
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar última posição: {e}"}), 500

@app.route('/api/positions/updates/<int:vehicle_id>', methods=['GET'])
def get_position_updates(vehicle_id):
    """Busca novas posições para um veículo desde um certo timestamp."""
    since_timestamp = request.args.get('since')
    if not since_timestamp:
        return jsonify({"erro": "Parâmetro 'since' é obrigatório"}), 400

    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                    SELECT 
                        ST_Y(LOCLATLONG) as latitude, 
                        ST_X(LOCLATLONG) as longitude,
                        DATAHORA, 
                        VELATU as velocidade_kmh
                    FROM 
                        localizacao
                    WHERE FK_VEICOD = %s AND DATAHORA > %s
                    ORDER BY DATAHORA ASC;
                """
                cursor.execute(query, (vehicle_id, since_timestamp))
                updates = cursor.fetchall()
                return jsonify(format_results(updates))
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar atualizações: {e}"}), 500

# ============================================
# BEHAVIORAL ENDPOINTS (DataDrivr Integration)
# ============================================
from . import behavioral_engine

# ============================================
# DIRIJABEM REPLAY ENDPOINTS
# ============================================
from .dirijabem_api import dirijabem_bp
app.register_blueprint(dirijabem_bp)

@app.route('/api/fleet/scores', methods=['GET'])
def get_fleet_scores():
    """
    Retorna scores comportamentais de todos os veículos

    Response:
    {
        "SIM-1000": 94.2,
        "SIM-1001": 42.3,
        ...
    }
    """
    try:
        scores = behavioral_engine.get_all_scores()
        return jsonify(scores)
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar scores: {e}"}), 500


@app.route('/api/fleet/events', methods=['GET'])
def get_fleet_events():
    """
    Retorna eventos comportamentais recentes

    Query params:
    - limit: número de eventos (default: 50)
    - device_id: filtrar por veículo (opcional)

    Response:
    [
        {
            "device_id": "SIM-1000",
            "type": "harsh_brake",
            "lat": -23.5505,
            "lon": -46.6333,
            "timestamp": "2026-01-27T14:35:22",
            "severity": "high",
            "icon": "🛑",
            ...
        },
        ...
    ]
    """
    try:
        limit = int(request.args.get('limit', 50))
        device_id = request.args.get('device_id')

        events = behavioral_engine.get_recent_events(limit=limit, device_id=device_id)
        return jsonify(events)
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar eventos: {e}"}), 500


@app.route('/api/fleet/stats', methods=['GET'])
def get_fleet_stats():
    """
    Retorna estatísticas agregadas da frota

    Response:
    {
        "fleet_avg": 72.4,
        "total_vehicles": 10,
        "events_today": 143,
        "top3": [
            {"device_id": "SIM-1001", "score": 94.2},
            ...
        ],
        "bottom3": [
            {"device_id": "SIM-1008", "score": 42.3},
            ...
        ]
    }
    """
    try:
        stats = behavioral_engine.get_fleet_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar estatísticas: {e}"}), 500


@app.route('/api/vehicles/<device_id>/score', methods=['GET'])
def get_vehicle_score(device_id):
    """
    Retorna score de um veículo específico

    Response:
    {
        "device_id": "SIM-1000",
        "score": 85.3
    }
    """
    try:
        score = behavioral_engine.get_vehicle_score(device_id)
        return jsonify({
            "device_id": device_id,
            "score": score
        })
    except Exception as e:
        return jsonify({"erro": f"Erro ao buscar score: {e}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)
