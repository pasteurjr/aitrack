import os
import time
import json
import math
import subprocess
from threading import Thread
from pathlib import Path
from server.routes_loader import load_routes

# Configurações
ENV = os.environ.copy()
ENV.setdefault("AITRACK_USE_FILE_STORAGE", "1")
ENV.setdefault("AITRACK_FILE_PATH", "positions_log.jsonl")

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9000

# Rotas (mesmas do simulador)
ROUTES = load_routes(min_points=30)

TOLERANCE = 0.001  # ~111m
N_VEHICLES = 10
POINTS_TARGET = 10

def is_point_on_route(point, route_coords):
    for (plat, plon) in route_coords:
        d = math.hypot(point[0] - plat, point[1] - plon)
        if d <= TOLERANCE:
            return True
    return False

def expected_route_name_for_device(device_id: str) -> str:
    # espelha a lógica do simulador após alteração (protocol alterna suntech/queclink; mapeamento de rota por índice)
    base = int(device_id.split('-')[1])
    i = base - 1000
    names = list(ROUTES.keys())
    return names[i % len(names)]

def start_socket_server():
    return subprocess.Popen(["python", "-c", "from server.socket_server import start_server; start_server()"], env=ENV)

def start_simulator():
    return subprocess.Popen(["python", "simulator.py"], env=ENV)

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
    # limpar arquivo
    p = Path(ENV["AITRACK_FILE_PATH"])
    if p.exists():
        p.unlink()

    srv = start_socket_server()
    time.sleep(0.5)
    sim = start_simulator()

    try:
        deadline = time.time() + 180  # 3 min máx
        passed = False
        while time.time() < deadline:
            time.sleep(2)
            all_positions = load_positions(p)
            by_dev = {}
            for r in all_positions:
                did = r.get("device_id")
                if not did or did == "MAXTRACK-ANON":
                    # ignorar maxtrack anon, não deve ocorrer após desativação
                    continue
                by_dev.setdefault(did, []).append((r.get("latitude"), r.get("longitude")))

            ok = True
            for i in range(N_VEHICLES):
                dev = f"SIM-{1000 + i}"
                pts = by_dev.get(dev, [])[-POINTS_TARGET:]
                if len(pts) < POINTS_TARGET:
                    ok = False
                    break
                route_name = expected_route_name_for_device(dev)
                route = ROUTES[route_name]
                # verificar todos os pontos
                if not all(is_point_on_route(pt, route) for pt in pts):
                    ok = False
                    break
            if ok:
                passed = True
                break

        print("STATUS:", "SUCESSO" if passed else "FALHA")
        if not passed:
            # log curto para debug
            print("Coleta insuficiente ou pontos fora de rota.")
    finally:
        sim.terminate()
        srv.terminate()
        sim.wait(timeout=5)
        srv.wait(timeout=5)

if __name__ == "__main__":
    main()
