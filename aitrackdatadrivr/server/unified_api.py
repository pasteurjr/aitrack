"""
Unified API - Integra dados de tracker e dirijabem
Retorna visão unificada de todos os veículos independente da fonte
"""

from flask import Blueprint, jsonify
import mysql.connector
from datetime import datetime

# Create blueprint
unified_bp = Blueprint('unified', __name__, url_prefix='/api/unified')

# Database configs
TRACKER_DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'tracker'
}

DIRIJABEM_DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'dirijabem'
}


def get_tracker_connection():
    """Get tracker database connection"""
    return mysql.connector.connect(**TRACKER_DB_CONFIG)


def get_dirijabem_connection():
    """Get dirijabem database connection"""
    return mysql.connector.connect(**DIRIJABEM_DB_CONFIG)


@unified_bp.route('/vehicles', methods=['GET'])
def get_all_vehicles():
    """
    Retorna TODOS os veículos (tracker + dirijabem) com dados unificados
    """
    try:
        conn = get_tracker_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar todos os veículos unificados
        cursor.execute("""
            SELECT id, device_id, codusu, placa, tipo, descricao, ativo
            FROM veiculo_unificado
            WHERE ativo = TRUE
            ORDER BY id
        """)

        vehicles = cursor.fetchall()
        cursor.close()
        conn.close()

        # Para cada veículo, buscar dados específicos
        result = []
        for vehicle in vehicles:
            unified_data = {
                'id': vehicle['id'],
                'placa': vehicle['placa'],
                'tipo': vehicle['tipo'],
                'descricao': vehicle['descricao'],
                'fonte': None,
                'posicao_atual': None,
                'ultima_viagem': None,
                'score': None,
                'status': 'offline'
            }

            # Se tem device_id, buscar dados do tracker
            if vehicle['device_id']:
                tracker_data = get_tracker_data(vehicle['device_id'])
                if tracker_data:
                    unified_data['fonte'] = 'tracker'
                    unified_data['posicao_atual'] = tracker_data
                    unified_data['status'] = 'online' if tracker_data else 'offline'

            # Se tem codusu, buscar dados do dirijabem
            if vehicle['codusu']:
                dirijabem_data = get_dirijabem_data(vehicle['codusu'])
                if dirijabem_data:
                    if unified_data['fonte']:
                        unified_data['fonte'] = 'both'
                    else:
                        unified_data['fonte'] = 'dirijabem'

                    unified_data['ultima_viagem'] = dirijabem_data.get('ultima_viagem')
                    unified_data['score'] = dirijabem_data.get('score')

            result.append(unified_data)

        return jsonify({
            'success': True,
            'total': len(result),
            'vehicles': result
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@unified_bp.route('/vehicle/<placa>', methods=['GET'])
def get_vehicle_details(placa):
    """
    Retorna detalhes completos de um veículo específico
    Busca em ambos os bancos se necessário
    """
    try:
        conn = get_tracker_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar veículo na tabela unificada
        cursor.execute("""
            SELECT id, device_id, codusu, placa, tipo, descricao
            FROM veiculo_unificado
            WHERE placa = %s AND ativo = TRUE
        """, (placa,))

        vehicle = cursor.fetchone()
        cursor.close()
        conn.close()

        if not vehicle:
            return jsonify({'success': False, 'error': 'Veículo não encontrado'}), 404

        # Montar dados completos
        result = {
            'id': vehicle['id'],
            'placa': vehicle['placa'],
            'tipo': vehicle['tipo'],
            'descricao': vehicle['descricao'],
            'tracker': None,
            'dirijabem': None
        }

        # Buscar dados do tracker se disponível
        if vehicle['device_id']:
            result['tracker'] = get_tracker_data_full(vehicle['device_id'])

        # Buscar dados do dirijabem se disponível
        if vehicle['codusu']:
            result['dirijabem'] = get_dirijabem_data_full(vehicle['codusu'])

        return jsonify({
            'success': True,
            'vehicle': result
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def get_tracker_data(device_id):
    """Busca última posição GPS do tracker"""
    try:
        conn = get_tracker_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                ST_Y(LOCLATLONG) as lat,
                ST_X(LOCLATLONG) as lon,
                VELATU as velocidade,
                DATAHORA as timestamp
            FROM localizacao
            WHERE VEI_DEVICE_ID = %s
            ORDER BY DATAHORA DESC
            LIMIT 1
        """, (device_id,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result

    except:
        return None


def get_tracker_data_full(device_id):
    """Busca dados completos do tracker"""
    try:
        conn = get_tracker_connection()
        cursor = conn.cursor(dictionary=True)

        # Última posição
        cursor.execute("""
            SELECT
                ST_Y(LOCLATLONG) as lat,
                ST_X(LOCLATLONG) as lon,
                VELATU as velocidade,
                ORIENT as direcao,
                ALTITUDE as altitude,
                DATAHORA as timestamp
            FROM localizacao
            WHERE VEI_DEVICE_ID = %s
            ORDER BY DATAHORA DESC
            LIMIT 1
        """, (device_id,))

        posicao = cursor.fetchone()

        # Histórico recente (últimos 100 pontos)
        cursor.execute("""
            SELECT
                ST_Y(LOCLATLONG) as lat,
                ST_X(LOCLATLONG) as lon,
                VELATU as velocidade,
                DATAHORA as timestamp
            FROM localizacao
            WHERE VEI_DEVICE_ID = %s
            ORDER BY DATAHORA DESC
            LIMIT 100
        """, (device_id,))

        historico = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            'device_id': device_id,
            'posicao_atual': posicao,
            'historico': historico,
            'total_pontos': len(historico)
        }

    except:
        return None


def get_dirijabem_data(codusu):
    """Busca dados resumidos do dirijabem"""
    try:
        conn = get_dirijabem_connection()
        cursor = conn.cursor(dictionary=True)

        # Última viagem
        cursor.execute("""
            SELECT
                CODVIA,
                DATAHORINI,
                DATAHORFIN,
                SCORE,
                DISTANCIA,
                DURACAO
            FROM viagem
            WHERE CODUSU = %s
            ORDER BY DATAHORINI DESC
            LIMIT 1
        """, (codusu,))

        viagem = cursor.fetchone()
        cursor.close()
        conn.close()

        if viagem:
            return {
                'ultima_viagem': viagem,
                'score': viagem.get('SCORE')
            }

        return None

    except:
        return None


def get_dirijabem_data_full(codusu):
    """Busca dados completos do dirijabem"""
    try:
        conn = get_dirijabem_connection()
        cursor = conn.cursor(dictionary=True)

        # Últimas 10 viagens
        cursor.execute("""
            SELECT
                CODVIA,
                DATAHORINI,
                DATAHORFIN,
                SCORE,
                DISTANCIA,
                DURACAO,
                OST, OSA, OSP,
                SAM, SAA,
                BRP, BRM, BRA
            FROM viagem
            WHERE CODUSU = %s
            ORDER BY DATAHORINI DESC
            LIMIT 10
        """, (codusu,))

        viagens = cursor.fetchall()

        # Score médio
        score_medio = sum(v['SCORE'] for v in viagens if v['SCORE']) / len(viagens) if viagens else 0

        cursor.close()
        conn.close()

        return {
            'codusu': codusu,
            'viagens': viagens,
            'total_viagens': len(viagens),
            'score_medio': round(score_medio, 1)
        }

    except:
        return None


@unified_bp.route('/stats', methods=['GET'])
def get_unified_stats():
    """Estatísticas gerais do sistema unificado"""
    try:
        conn = get_tracker_connection()
        cursor = conn.cursor(dictionary=True)

        # Contar veículos por tipo
        cursor.execute("""
            SELECT
                tipo,
                COUNT(*) as total
            FROM veiculo_unificado
            WHERE ativo = TRUE
            GROUP BY tipo
        """)

        stats_tipo = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'por_tipo': stats_tipo,
                'total_geral': sum(s['total'] for s in stats_tipo)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
