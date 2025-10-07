import json
from pathlib import Path
from typing import Dict, List, Tuple

# Fallback hardcoded (5 pontos) caso não exista config externa
FALLBACK_ROUTES: Dict[str, List[Tuple[float, float]]] = {
    "908T-10": [(-23.5505, -46.6333), (-23.5510, -46.6345), (-23.5520, -46.6360), (-23.5535, -46.6380), (-23.5550, -46.6400)],
    "8700-10": [(-23.5610, -46.6550), (-23.5600, -46.6570), (-23.5590, -46.6590), (-23.5580, -46.6610), (-23.5570, -46.6630)],
    "5111-10": [(-23.6820, -46.6960), (-23.6800, -46.6955), (-23.6780, -46.6950), (-23.6760, -46.6945), (-23.6740, -46.6940)],
    "175T-10": [(-23.4960, -46.6290), (-23.4970, -46.6310), (-23.4980, -46.6330), (-23.4990, -46.6350), (-23.5000, -46.6370)],
    "647A-10": [(-23.6100, -46.7000), (-23.6110, -46.6980), (-23.6120, -46.6960), (-23.6130, -46.6940), (-23.6140, -46.6920)],
}


def _interpolate_segment(a: Tuple[float, float], b: Tuple[float, float], steps: int):
    lat1, lon1 = a
    lat2, lon2 = b
    for i in range(steps):
        t = i / float(steps)
        yield (lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t)


def densify_route(points: List[Tuple[float, float]], min_points: int = 30) -> List[Tuple[float, float]]:
    if len(points) >= min_points:
        return points
    if len(points) < 2:
        return points
    # Distribui passos por segmento para atingir pelo menos min_points
    segs = len(points)
    total_steps = max(min_points, segs)
    steps_per_seg = max(2, total_steps // segs)
    densified = []
    for i in range(segs):
        a = points[i]
        b = points[(i + 1) % segs]
        densified.extend(list(_interpolate_segment(a, b, steps_per_seg)))
    return densified[:max(min_points, len(densified))]


def load_routes(min_points: int = 30) -> Dict[str, List[Tuple[float, float]]]:
    cfg_path = Path("config/routes.json")
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            routes = {name: [(float(lat), float(lon)) for lat, lon in coords] for name, coords in data.items()}
            # valida e densifica
            for k, v in list(routes.items()):
                if len(v) < min_points:
                    routes[k] = densify_route(v, min_points)
            return routes
        except Exception:
            pass
    # fallback + densificação
    return {k: densify_route(v, min_points) for k, v in FALLBACK_ROUTES.items()}

