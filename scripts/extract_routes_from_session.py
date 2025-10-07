#!/usr/bin/env python3
import re
import json
from pathlib import Path
from math import hypot

SESSION_FILE = Path("sessao26091027.txt")
OUT_FILE = Path("config/routes.json")


def extract_pairs(text: str):
    # Captura pares no formato [-46.xxxxx, -23.xxxxx] (lon, lat) do trecho colado na sessão
    rx = re.compile(r"\[\s*(-46\.[0-9]+)\s*,\s*(-23\.[0-9]+)\s*\]")
    return [(float(b), float(a)) for a, b in rx.findall(text)]  # inverte p/ (lat, lon)


def segment_routes(coords, jump_deg=0.02, min_len=30):
    """
    Separa a sequência em grupos quando houver "saltos" grandes (ex.: > ~2.2km).
    Retorna lista de listas de (lat, lon) com tamanho >= min_len.
    """
    groups = []
    current = []
    prev = None
    for c in coords:
        if prev is None:
            current.append(c)
            prev = c
            continue
        d = hypot(c[0] - prev[0], c[1] - prev[1])
        if d > jump_deg and len(current) >= min_len:
            groups.append(current)
            current = [c]
        else:
            current.append(c)
        prev = c
    if len(current) >= min_len:
        groups.append(current)
    return groups


def main():
    if not SESSION_FILE.exists():
        print(f"Arquivo não encontrado: {SESSION_FILE}")
        return 1
    text = SESSION_FILE.read_text(encoding="utf-8", errors="ignore")
    coords = extract_pairs(text)
    if len(coords) < 30:
        print(f"Poucos pontos extraídos: {len(coords)} (<30). Verifique o arquivo de sessão.")
        return 2
    groups = segment_routes(coords, jump_deg=0.02, min_len=30)
    if not groups:
        groups = [coords]

    # Seleciona até 5 rotas na ordem em que aparecem
    keys = ["908T-10", "8700-10", "5111-10", "175T-10", "647A-10"]
    routes = {}
    for k, g in zip(keys, groups):
        routes[k] = g
    # Se sobrar chave sem grupo, duplica a primeira para preencher (opcional)
    if len(routes) < len(keys):
        for k in keys[len(routes):]:
            routes[k] = groups[0]
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(routes, ensure_ascii=False), encoding="utf-8")
    print(f"Gerado {OUT_FILE} com {[len(v) for v in routes.values()]} pontos por rota.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
