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
    """Busca veículos que transmitiram nos últimos 10 segundos (ONLINE)."""
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                    SELECT
                        v.VEICOD, v.VEIPLACA
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)
