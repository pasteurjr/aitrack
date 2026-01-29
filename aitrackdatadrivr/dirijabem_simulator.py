#!/usr/bin/env python3
"""
Dirijabem Trip Replay System
Replays real trips from dirijabem database point-by-point
"""

import json
import time
import random
import mysql.connector
from datetime import datetime
from threading import Thread, Lock
from pathlib import Path

# Configuration
SPEED_MULTIPLIER = 1  # 1 = real-time, 10 = 10x faster
ROUTES_FILE = 'config/dirijabem_routes.json'

# Database connection
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'producao',
    'password': '112358123',
    'database': 'dirijabem',
    'pool_name': 'dirijabem_pool',
    'pool_size': 5
}

class TripReplay:
    """Manages replay of a single trip"""

    def __init__(self, codvia, route, resume_from_index=None):
        self.codvia = codvia
        self.points = route['points']
        self.original_metrics = route['metrics']

        # Resume from specific index (based on points already saved in DB)
        if resume_from_index is not None:
            self.current_index = resume_from_index
            print(f"[TripReplay] Resuming CODVIA={codvia} from index {resume_from_index}/{len(self.points)}")
        else:
            self.current_index = 0
            print(f"[TripReplay] Starting CODVIA={codvia} from beginning, total points: {len(self.points)}")

    def has_next_point(self):
        """Check if there are more points to emit"""
        return self.current_index < len(self.points)

    def get_next_point(self):
        """Get next point and advance index"""
        if not self.has_next_point():
            return None

        point = self.points[self.current_index]
        self.current_index += 1
        return point

    def get_wait_time(self, next_point):
        """Calculate wait time until next point (respecting SPEED_MULTIPLIER)"""
        if self.current_index <= 0 or self.current_index >= len(self.points):
            return 1.0  # Default 1 second

        current = self.points[self.current_index - 1]
        prev_time = datetime.fromisoformat(current['timestamp'])
        next_time = datetime.fromisoformat(next_point['timestamp'])

        delta_seconds = (next_time - prev_time).total_seconds()
        return max(0.1, delta_seconds / SPEED_MULTIPLIER)  # Minimum 0.1s

class DirijabemReplayManager:
    """Manages multiple concurrent trip replays"""

    def __init__(self):
        self.active_trips = {}  # {codusu: TripReplay instance}
        self.trips_lock = Lock()
        self.routes = self._load_routes()
        self.db_pool = None
        self.running = False

    def _load_routes(self):
        """Load routes from JSON file"""
        routes_path = Path(ROUTES_FILE)
        if not routes_path.exists():
            raise FileNotFoundError(f"Routes file not found: {ROUTES_FILE}")

        with open(routes_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_db_connection(self):
        """Get database connection from pool"""
        if self.db_pool is None:
            self.db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
        return self.db_pool.get_connection()

    def _check_in_progress_trip(self, codusu):
        """Check if user has trip in progress (DATAHORFIN = '1900-01-01')
        Returns (CODVIA, points_count) or None"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT v.CODVIA, COUNT(l.LOCDADCOD) as points_count
            FROM viagem v
            LEFT JOIN localizacaodados l ON l.CODVIA = v.CODVIA
            WHERE v.CODUSU = %s AND v.DATAHORFIN = '1900-01-01 00:00:00'
            GROUP BY v.CODVIA
            ORDER BY v.DATAHORINI DESC
            LIMIT 1
        """, (codusu,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result

    def _create_new_trip(self, codusu, original_codvia):
        """Create new viagem record, returns new CODVIA"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO viagem (CODUSU, DATAHORINI, DATAHORFIN, PLACA)
            VALUES (%s, NOW(), '1900-01-01 00:00:00', 'REPLAY')
        """, (codusu,))

        new_codvia = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[DIRIJABEM] Created new trip CODVIA={new_codvia} for user {codusu} (original: {original_codvia})")
        return new_codvia

    def _save_point(self, codvia, point):
        """Save GPS point to localizacaodados"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO localizacaodados (CODVIA, DATAHORA, coords, VELATU)
                VALUES (%s, NOW(), ST_PointFromText('POINT(%s %s)'), %s)
            """, (codvia, point['lon'], point['lat'], point['speed']))

            conn.commit()
        except Exception as e:
            print(f"[DIRIJABEM] Error saving point: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def _finalize_trip(self, codvia, metrics):
        """Copy metrics from original trip and set DATAHORFIN"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE viagem SET
                    DATAHORFIN = NOW(),
                    OST = %s, OSA = %s, GAA = %s, OSP = %s,
                    SAM = %s, SAA = %s,
                    BRP = %s, BRM = %s, BRA = %s,
                    GAP = %s, GAN = %s, GAM = %s,
                    SCORE = %s
                WHERE CODVIA = %s
            """, (
                metrics['OST'], metrics['OSA'], metrics['GAA'], metrics['OSP'],
                metrics['SAM'], metrics['SAA'],
                metrics['BRP'], metrics['BRM'], metrics['BRA'],
                metrics['GAP'], metrics['GAN'], metrics['GAM'],
                metrics['SCORE'],
                codvia
            ))

            conn.commit()
            print(f"[DIRIJABEM] Trip CODVIA={codvia} completed, metrics copied (SCORE={metrics['SCORE']})")
        except Exception as e:
            print(f"[DIRIJABEM] Error finalizing trip: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def start_user_trip(self, codusu):
        """Start or resume trip for user (idempotent - can call multiple times)"""
        if str(codusu) not in self.routes:
            print(f"[DIRIJABEM] User {codusu} not found in routes")
            return False

        user_data = self.routes[str(codusu)]
        username = user_data['username']

        with self.trips_lock:
            # IDEMPOTENT: If trip already active in memory, do nothing
            if codusu in self.active_trips:
                print(f"[DIRIJABEM] ✅ Trip already active for {username}, continuing...")
                return True

            # Check for in-progress trip in database
            in_progress = self._check_in_progress_trip(codusu)

            if in_progress:
                codvia, points_count = in_progress
                print(f"[DIRIJABEM] 🔄 Resuming trip for {username} (CODVIA={codvia}) from point {points_count}")

                # Find original route by CODVIA
                original_route = None
                for route in user_data['routes']:
                    if route['codvia'] == codvia:
                        original_route = route
                        break

                if not original_route:
                    print(f"[DIRIJABEM] Warning: Original route not found, choosing random")
                    original_route = random.choice(user_data['routes'])

                # Resume from point index (not timestamp)
                self.active_trips[codusu] = TripReplay(codvia, original_route, resume_from_index=points_count)
            else:
                # Start new random trip
                route = random.choice(user_data['routes'])
                original_codvia = route['codvia']
                new_codvia = self._create_new_trip(codusu, original_codvia)

                print(f"[DIRIJABEM] 🆕 Starting new trip for {username} (route {original_codvia} → CODVIA={new_codvia})")
                self.active_trips[codusu] = TripReplay(new_codvia, route)

        return True

    def stop_user_trip(self, codusu):
        """Stop active trip for user"""
        with self.trips_lock:
            if codusu in self.active_trips:
                del self.active_trips[codusu]
                print(f"[DIRIJABEM] Stopped trip for user {codusu}")
                return True
        return False

    def emit_points_loop(self):
        """Main loop that emits points for all active trips"""
        print("[DIRIJABEM] Starting replay loop")

        # Track last emission time for each user
        last_emission = {}

        while self.running:
            now = time.time()

            with self.trips_lock:
                finished_users = []

                for codusu, replay in list(self.active_trips.items()):
                    # Initialize last emission time
                    if codusu not in last_emission:
                        last_emission[codusu] = 0

                    # Check if it's time to emit next point
                    time_since_last = now - last_emission[codusu]

                    if replay.has_next_point():
                        # Get wait time for next point
                        if replay.current_index > 0:
                            current = replay.points[replay.current_index - 1]
                            next_point = replay.points[replay.current_index]
                            prev_time = datetime.fromisoformat(current['timestamp'])
                            next_time = datetime.fromisoformat(next_point['timestamp'])
                            delta_seconds = (next_time - prev_time).total_seconds()
                            wait_time = max(0.1, delta_seconds / SPEED_MULTIPLIER)
                        else:
                            wait_time = 0.1  # First point, emit immediately

                        # Only emit if enough time has passed
                        if time_since_last >= wait_time:
                            point = replay.get_next_point()
                            self._save_point(replay.codvia, point)
                            last_emission[codusu] = now
                            print(f"[DIRIJABEM] User {codusu}: Emitted point {replay.current_index}/{len(replay.points)}")
                    else:
                        # Trip finished
                        self._finalize_trip(replay.codvia, replay.original_metrics)
                        finished_users.append(codusu)
                        if codusu in last_emission:
                            del last_emission[codusu]

                # Remove finished trips
                for codusu in finished_users:
                    del self.active_trips[codusu]

            time.sleep(0.1)  # Small sleep to prevent CPU spinning

    def start(self):
        """Start the replay manager"""
        self.running = True
        replay_thread = Thread(target=self.emit_points_loop, daemon=True)
        replay_thread.start()
        print("[DIRIJABEM] Replay manager started")

    def stop(self):
        """Stop the replay manager"""
        self.running = False
        print("[DIRIJABEM] Replay manager stopped")

# Global instance
replay_manager = None

def get_replay_manager():
    """Get or create global replay manager instance"""
    global replay_manager
    if replay_manager is None:
        replay_manager = DirijabemReplayManager()
        replay_manager.start()
    return replay_manager

if __name__ == "__main__":
    print("Dirijabem Replay Simulator")
    print("Starting...")

    manager = get_replay_manager()

    print("Replay manager ready. Waiting for trip requests...")
    print(f"Speed multiplier: {SPEED_MULTIPLIER}x")
    print("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop()
