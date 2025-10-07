#!/usr/bin/env python3
"""
Baixa rotas de ônibus do OpenStreetMap via Overpass API e salva em config/routes.json.
Observação: requer internet e pode demorar. Ajuste a cidade/área conforme necessário.
"""
import json
import sys
import time
from typing import Dict, List, Tuple

import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def query_route(ref: str, city: str = "Sao Paulo") -> List[Tuple[float, float]]:
    """
    Busca geometria aproximada de uma rota de ônibus (relation type=route, route=bus, ref=ref) na área especificada.
    Retorna uma lista de (lat, lon). Pode conter 100+ pontos.
    """
    # Consulta por área + relação da rota
    q = f"""
    [out:json][timeout:60];
    area["name"="{city}"]["boundary"="administrative"]->.searchArea;
    rel["type"="route"]["route"="bus"]["ref"="{ref}"](area.searchArea);
    (._;>;);
    out geom;
    """
    resp = requests.post(OVERPASS_URL, data={"data": q})
    resp.raise_for_status()
    data = resp.json()
    coords: List[Tuple[float, float]] = []
    # Extrai geometria simplificada a partir dos ways membros
    ways = [el for el in data.get("elements", []) if el.get("type") == "way" and el.get("geometry")]
    for w in ways:
        for g in w["geometry"]:
            coords.append((g["lat"], g["lon"]))
    # Opcional: deduplicar consecutivos
    dedup: List[Tuple[float, float]] = []
    last = None
    for c in coords:
        if c != last:
            dedup.append(c)
            last = c
    return dedup


def main():
    if len(sys.argv) < 2:
        print("Uso: fetch_routes_overpass.py REF1 [REF2 ...] [--city 'Sao Paulo']")
        sys.exit(1)
    args = sys.argv[1:]
    city = "Sao Paulo"
    if "--city" in args:
        i = args.index("--city")
        city = args[i + 1]
        args = args[:i] + args[i + 2 :]
    refs = args
    routes: Dict[str, List[Tuple[float, float]]] = {}
    for ref in refs:
        print(f"Baixando rota {ref}…")
        coords = query_route(ref, city=city)
        print(f"  pontos: {len(coords)}")
        routes[ref] = coords
        time.sleep(1)
    # Salva em config/routes.json
    with open("config/routes.json", "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False)
    print("Rotas salvas em config/routes.json")


if __name__ == "__main__":
    main()

