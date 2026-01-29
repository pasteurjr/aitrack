#!/usr/bin/env python3
"""
Extract 100 real routes from dirijabem database (10 routes per top 10 users)
Saves to config/dirijabem_routes.json for replay system
"""

import json
import mysql.connector
from pathlib import Path
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'dirijabem'
}

# Top 10 users by trip count
TOP_USERS = [
    (1, "Pasteur Jr."),
    (614, "Pssteur 2"),
    (17, "daniela pereira"),
    (411, "dani"),
    (21, "Bruno Gomes Marques"),
    (239, "Reginaldo"),
    (617, "William"),
    (608, "Eudes"),
    (36, "Gabriela"),
    (70, "larissapimenta")
]

def get_user_routes(cursor, codusu, username):
    """Get 10 best trips for a user"""
    print(f"Extracting routes for {username} (CODUSU={codusu})...")

    # Get 10 trips with most GPS points (50-2000 range)
    query = """
        SELECT
            v.CODVIA,
            v.DISTANCIA,
            v.DURACAO,
            v.SCORE,
            v.OST, v.OSA, v.GAA, v.OSP,
            v.SAM, v.SAA,
            v.BRP, v.BRM, v.BRA,
            v.GAP, v.GAN, v.GAM,
            COUNT(l.LOCDADCOD) as num_points
        FROM viagem v
        JOIN localizacaodados l ON l.CODVIA = v.CODVIA
        WHERE v.CODUSU = %s
        GROUP BY v.CODVIA
        HAVING num_points >= 50 AND num_points <= 2000
        ORDER BY num_points DESC
        LIMIT 10
    """

    cursor.execute(query, (codusu,))
    trips = cursor.fetchall()

    routes = []
    for trip in trips:
        codvia = trip[0]

        # Get GPS points for this trip
        points_query = """
            SELECT
                ST_Y(coords) as lat,
                ST_X(coords) as lon,
                DATAHORA as timestamp,
                VELATU as speed
            FROM localizacaodados
            WHERE CODVIA = %s
            ORDER BY DATAHORA ASC
        """

        cursor.execute(points_query, (codvia,))
        points_data = cursor.fetchall()

        # Format points
        points = []
        for point in points_data:
            lat, lon, timestamp, speed = point
            if lat is not None and lon is not None:
                points.append({
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "speed": round(speed, 2) if speed else 0.0
                })

        if len(points) > 0:
            # Extract metrics (handle None values)
            metrics = {
                "OST": float(trip[4]) if trip[4] is not None else 0.0,
                "OSA": float(trip[5]) if trip[5] is not None else 0.0,
                "GAA": float(trip[6]) if trip[6] is not None else 0.0,
                "OSP": float(trip[7]) if trip[7] is not None else 0.0,
                "SAM": float(trip[8]) if trip[8] is not None else 0.0,
                "SAA": float(trip[9]) if trip[9] is not None else 0.0,
                "BRP": float(trip[10]) if trip[10] is not None else 0.0,
                "BRM": float(trip[11]) if trip[11] is not None else 0.0,
                "BRA": float(trip[12]) if trip[12] is not None else 0.0,
                "GAP": float(trip[13]) if trip[13] is not None else 0.0,
                "GAN": float(trip[14]) if trip[14] is not None else 0.0,
                "GAM": float(trip[15]) if trip[15] is not None else 0.0,
                "SCORE": float(trip[3]) if trip[3] is not None else 0.0
            }

            route = {
                "codvia": codvia,
                "points": points,
                "metrics": metrics,
                "distance": float(trip[1]) if trip[1] is not None else 0.0,
                "duration": float(trip[2]) if trip[2] is not None else 0.0
            }

            routes.append(route)
            print(f"  - Route {codvia}: {len(points)} points, {route['distance']:.1f}m, {route['duration']:.1f}min")

    return routes

def main():
    print("=" * 60)
    print("DIRIJABEM ROUTE EXTRACTION")
    print("=" * 60)
    print(f"Connecting to {DB_CONFIG['host']}:{DB_CONFIG['port']}...")

    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✓ Connected successfully\n")

        # Extract routes for all users
        all_routes = {}
        total_points = 0

        for codusu, username in TOP_USERS:
            routes = get_user_routes(cursor, codusu, username)

            if len(routes) > 0:
                all_routes[str(codusu)] = {
                    "username": username,
                    "routes": routes
                }

                # Count total points
                for route in routes:
                    total_points += len(route['points'])

                print(f"  ✓ Extracted {len(routes)} routes\n")
            else:
                print(f"  ⚠ No suitable routes found\n")

        cursor.close()
        conn.close()

        # Save to JSON
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)

        output_file = config_dir / 'dirijabem_routes.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_routes, f, indent=2, ensure_ascii=False)

        # Summary
        print("=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"✓ {len(all_routes)} users processed")
        print(f"✓ {sum(len(u['routes']) for u in all_routes.values())} total routes extracted")
        print(f"✓ {total_points:,} total GPS points")
        print(f"✓ File saved: {output_file}")
        print(f"✓ File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
        print("=" * 60)

    except mysql.connector.Error as err:
        print(f"\n✗ Database error: {err}")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
