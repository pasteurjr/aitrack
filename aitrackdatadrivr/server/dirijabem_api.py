"""
Dirijabem REST API
Endpoints for trip replay management
"""

from flask import Blueprint, jsonify, request
import mysql.connector
from dirijabem_simulator import get_replay_manager

# Create blueprint
dirijabem_bp = Blueprint('dirijabem', __name__, url_prefix='/api/dirijabem')

# Database connection config
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'dirijabem'
}

# Top 10 users
USERS = [
    {"codusu": 1, "name": "Pasteur Jr."},
    {"codusu": 614, "name": "Pssteur 2"},
    {"codusu": 17, "name": "daniela pereira"},
    {"codusu": 411, "name": "dani"},
    {"codusu": 21, "name": "Bruno Gomes Marques"},
    {"codusu": 239, "name": "Reginaldo"},
    {"codusu": 617, "name": "William"},
    {"codusu": 608, "name": "Eudes"},
    {"codusu": 36, "name": "Gabriela"},
    {"codusu": 70, "name": "larissapimenta"}
]

def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(**DB_CONFIG)

@dirijabem_bp.route('/users', methods=['GET'])
def get_users():
    """Returns list of top 10 users"""
    return jsonify(USERS)

@dirijabem_bp.route('/user/<int:codusu>/start', methods=['POST'])
def start_user_trip(codusu):
    """Starts or resumes trip for user"""
    try:
        manager = get_replay_manager()
        success = manager.start_user_trip(codusu)

        if success:
            return jsonify({"status": "started", "codusu": codusu})
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@dirijabem_bp.route('/user/<int:codusu>/stop', methods=['POST'])
def stop_user_trip(codusu):
    """Stops active trip for user"""
    try:
        manager = get_replay_manager()
        success = manager.stop_user_trip(codusu)

        if success:
            return jsonify({"status": "stopped", "codusu": codusu})
        else:
            return jsonify({"status": "not_active", "message": "No active trip"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@dirijabem_bp.route('/user/<int:codusu>/position', methods=['GET'])
def get_user_position(codusu):
    """Returns current position of user's active trip"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                v.CODVIA,
                ST_Y(l.coords) as lat,
                ST_X(l.coords) as lon,
                l.DATAHORA as timestamp,
                l.VELATU as speed
            FROM viagem v
            JOIN localizacaodados l ON l.CODVIA = v.CODVIA
            WHERE v.CODUSU = %s AND v.DATAHORFIN = '1900-01-01 00:00:00'
            ORDER BY l.DATAHORA DESC
            LIMIT 1
        """, (codusu,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return jsonify({
                "codvia": result['CODVIA'],
                "lat": float(result['lat']) if result['lat'] else None,
                "lon": float(result['lon']) if result['lon'] else None,
                "timestamp": result['timestamp'].isoformat() if result['timestamp'] else None,
                "speed": float(result['speed']) if result['speed'] else 0.0
            })
        else:
            return jsonify({"status": "no_active_trip"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dirijabem_bp.route('/user/<int:codusu>/last-point', methods=['GET'])
def get_user_last_point(codusu):
    """Returns ONLY the last point of active trip (incremental fetch)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                ST_Y(l.coords) as lat,
                ST_X(l.coords) as lon,
                l.DATAHORA as timestamp,
                l.VELATU as speed
            FROM viagem v
            JOIN localizacaodados l ON l.CODVIA = v.CODVIA
            WHERE v.CODUSU = %s AND v.DATAHORFIN = '1900-01-01 00:00:00'
            ORDER BY l.DATAHORA DESC
            LIMIT 1
        """, (codusu,))

        point = cursor.fetchone()
        cursor.close()
        conn.close()

        if point and point['lat'] is not None and point['lon'] is not None:
            return jsonify({
                "lat": float(point['lat']),
                "lon": float(point['lon']),
                "timestamp": point['timestamp'].isoformat() if point['timestamp'] else None,
                "speed": float(point['speed']) if point['speed'] else 0.0
            })
        else:
            return jsonify(None)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dirijabem_bp.route('/user/<int:codusu>/route', methods=['GET'])
def get_user_route(codusu):
    """Returns all points of active trip"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First check if there's an active trip
        cursor.execute("""
            SELECT CODVIA, DATAHORFIN
            FROM viagem
            WHERE CODUSU = %s AND DATAHORFIN = '1900-01-01 00:00:00'
            ORDER BY DATAHORINI DESC
            LIMIT 1
        """, (codusu,))

        active_trip = cursor.fetchone()
        print(f"[API-ROUTE] User {codusu}: Active trip = {active_trip}")

        if not active_trip:
            cursor.close()
            conn.close()
            print(f"[API-ROUTE] User {codusu}: No active trip found")
            return jsonify([])

        codvia = active_trip['CODVIA']
        print(f"[API-ROUTE] User {codusu}: Fetching points for CODVIA={codvia}")

        cursor.execute("""
            SELECT
                ST_Y(l.coords) as lat,
                ST_X(l.coords) as lon,
                l.DATAHORA as timestamp,
                l.VELATU as speed
            FROM localizacaodados l
            WHERE l.CODVIA = %s
            ORDER BY l.DATAHORA ASC
        """, (codvia,))

        points = cursor.fetchall()
        print(f"[API-ROUTE] User {codusu}: Found {len(points)} points")

        cursor.close()
        conn.close()

        # Format points
        formatted_points = []
        for point in points:
            if point['lat'] is not None and point['lon'] is not None:
                formatted_points.append({
                    "lat": float(point['lat']),
                    "lon": float(point['lon']),
                    "timestamp": point['timestamp'].isoformat() if point['timestamp'] else None,
                    "speed": float(point['speed']) if point['speed'] else 0.0
                })

        print(f"[API-ROUTE] User {codusu}: Returning {len(formatted_points)} formatted points")
        if len(formatted_points) > 0:
            print(f"[API-ROUTE] First point: lat={formatted_points[0]['lat']}, lon={formatted_points[0]['lon']}")

        return jsonify(formatted_points)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dirijabem_bp.route('/user/<int:codusu>/status', methods=['GET'])
def get_user_status(codusu):
    """Returns status of user's trip (active/inactive)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                v.CODVIA,
                v.DATAHORINI as start_time,
                COUNT(l.LOCDADCOD) as points_count
            FROM viagem v
            LEFT JOIN localizacaodados l ON l.CODVIA = v.CODVIA
            WHERE v.CODUSU = %s AND v.DATAHORFIN = '1900-01-01 00:00:00'
            GROUP BY v.CODVIA, v.DATAHORINI
            ORDER BY v.DATAHORINI DESC
            LIMIT 1
        """, (codusu,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return jsonify({
                "status": "active",
                "codvia": result['CODVIA'],
                "start_time": result['start_time'].isoformat() if result['start_time'] else None,
                "points_count": result['points_count']
            })
        else:
            return jsonify({"status": "inactive"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
