import os
import time
import json
import math
import random
from datetime import datetime
from pathlib import Path

from server.env_loader import load_dotenv  # noqa: E402
load_dotenv()
os.environ.setdefault("AITRACK_USE_FILE_STORAGE", "1")
os.environ.setdefault("AITRACK_FILE_PATH", "positions_log.jsonl")
from server.db_handler import save_location  # noqa: E402  (carrega DB/file cfg do .env)
from server.routes_loader import load_routes  # noqa: E402

ROUTES = load_routes(min_points=30)

TOLERANCE = 0.001
N_VEHICLES = 10
POINTS_PER_VEHICLE = 10


def is_point_on_route(point, route_coords):
    for (plat, plon) in route_coords:
        d = math.hypot(point[0] - plat, point[1] - plon)
        if d <= TOLERANCE:
            return True
    return False


def expected_route_name_for_device(device_id: str) -> str:
    base = int(device_id.split('-')[1])
    i = base - 1000
    names = list(ROUTES.keys())
    return names[i % len(names)]


def gen_point(route, idx):
    lat, lon = route[idx % len(route)]
    lat += random.uniform(-0.0001, 0.0001)
    lon += random.uniform(-0.0001, 0.0001)
    return lat, lon


def write_point(device_id, protocol, lat, lon):
    data = {
        'protocol': protocol,
        'device_id': device_id,
        'timestamp': datetime.utcnow().isoformat(),
        'gps_status': True,
        'latitude': lat,
        'longitude': lon,
        'speed': random.uniform(20, 60),
        'heading': random.uniform(0, 359),
        'ignition': True,
        'battery_voltage': random.uniform(12.0, 14.5),
        'panic': False,
        'altitude': None
    }
    # addr é ignorado internamente; passar dummy
    save_location(data, ("127.0.0.1", 0))


def load_positions(path: Path):
    data = []
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except Exception:
                continue
    return data


def main():
    p = Path(os.environ["AITRACK_FILE_PATH"])
    if p.exists():
        p.unlink()

    route_names = list(ROUTES.keys())
    # Gerar rapidamente 10 pontos por veículo
    for i in range(N_VEHICLES):
        device_id = f"SIM-{1000 + i}"
        route = ROUTES[route_names[i % len(route_names)]]
        protocol = ['suntech', 'queclink'][i % 2]
        for k in range(POINTS_PER_VEHICLE):
            lat, lon = gen_point(route, k)
            write_point(device_id, protocol, lat, lon)

    # Verificar
    positions = load_positions(p)
    by_dev = {}
    for r in positions:
        did = r.get("device_id")
        by_dev.setdefault(did, []).append((r.get("latitude"), r.get("longitude")))

    ok = True
    for i in range(N_VEHICLES):
        dev = f"SIM-{1000 + i}"
        pts = by_dev.get(dev, [])
        if len(pts) < POINTS_PER_VEHICLE:
            ok = False
            break
        route_name = expected_route_name_for_device(dev)
        route = ROUTES[route_name]
        if not all(is_point_on_route(pt, route) for pt in pts):
            ok = False
            break

    print("STATUS:", "SUCESSO" if ok else "FALHA")


if __name__ == "__main__":
    main()
