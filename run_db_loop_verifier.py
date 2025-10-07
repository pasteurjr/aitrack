import os
import time
import math
from datetime import datetime
import mysql.connector
from server.routes_loader import load_routes

DB_CONFIG = {
    'host': os.getenv('AITRACK_DB_HOST', 'camerascasas.no-ip.info'),
    'port': int(os.getenv('AITRACK_DB_PORT', '3307')),
    'user': os.getenv('AITRACK_DB_USER', 'scadabr'),
    'password': os.getenv('AITRACK_DB_PASSWORD', 'scadabr'),
    'database': os.getenv('AITRACK_DB_NAME', 'tracker'),
}

ROUTES = load_routes(min_points=30)

TOLERANCE = 0.001
SIMULATOR_IDS = [f"SIM-{1000 + i}" for i in range(10)]
# IMPORTANTE: os simuladores geram timestamps em UTC (via time.gmtime()).
# Para evitar descasamento de fuso (ex.: hora local -03:00), usamos UTC aqui
# como baseline quando o veículo ainda não possui dados.
START_TS = datetime.utcnow()
BASELINE = None  # mapeia did -> timestamp máximo já existente no início
STRICT_MODE = os.getenv('AITRACK_VERIFY_STRICT', '0') == '1'  # se 1, exige 10 pontos novos após baseline


def expected_route_name_for_device(device_id: str) -> str:
    base = int(device_id.split('-')[1])
    i = base - 1000
    names = list(ROUTES.keys())
    return names[i % len(names)]


def is_point_on_route(lat, lon, route_coords):
    for (plat, plon) in route_coords:
        d = math.hypot(lat - plat, lon - plon)
        if d <= TOLERANCE:
            return True
    return False


def closest_route_point(lat, lon, route_coords):
    """Retorna (index, (plat, plon), distancia_graus, distancia_metros_aprox)."""
    best_i, best_p, best_d = None, None, 1e9
    for i, (plat, plon) in enumerate(route_coords):
        d = math.hypot(lat - plat, lon - plon)
        if d < best_d:
            best_i, best_p, best_d = i, (plat, plon), d
    return best_i, best_p, best_d, best_d * 111000.0  # ~111km por grau


def fetch_baseline(conn):
    """Coleta o timestamp máximo existente por veículo no início do verificador."""
    base = {}
    cursor = conn.cursor(dictionary=True)
    for did in SIMULATOR_IDS:
        cursor.execute("SELECT VEICOD FROM veiculos WHERE VEI_DEVICE_ID = %s", (did,))
        v = cursor.fetchone()
        if not v:
            # Sem veículo ainda: baseline sem timestamp
            base[did] = None
            continue
        veicod = v['VEICOD']
        cursor.execute(
            "SELECT MAX(DATAHORA) AS mx FROM localizacao WHERE FK_VEICOD = %s",
            (veicod,),
        )
        row = cursor.fetchone()
        base[did] = row['mx'] if row and row['mx'] else None
    return base


def check_all(conn):
    """Retorna (ok, dados, progresso) onde dados inclui pontos por veículo para relatório
    e progresso é um dict did -> qtd_pontos_novos.
    """
    cursor = conn.cursor(dictionary=True)
    report_data = {}
    progress = {}
    for did in SIMULATOR_IDS:
        # obtém VEICOD
        cursor.execute("SELECT VEICOD FROM veiculos WHERE VEI_DEVICE_ID = %s", (did,))
        v = cursor.fetchone()
        if not v:
            progress[did] = 0
            return False, {}, progress
        veicod = v['VEICOD']
        if STRICT_MODE:
            # Buscar pontos e filtrar apenas os gerados após o baseline deste verificador
            cursor.execute(
                """
                SELECT ST_Y(LOCLATLONG) as lat, ST_X(LOCLATLONG) as lon, DATAHORA as ts
                FROM localizacao
                WHERE FK_VEICOD = %s
                ORDER BY DATAHORA ASC
                LIMIT 1000
                """,
                (veicod,),
            )
            all_rows = cursor.fetchall()
            base_ts = BASELINE.get(did)
            # Se não havia baseline (veículo novo sem dados), considerar tudo após START_TS (UTC)
            if base_ts is None:
                rows = [r for r in all_rows if r.get('ts') and r['ts'] >= START_TS]
            else:
                rows = [r for r in all_rows if r.get('ts') and r['ts'] > base_ts]
            # Mantém apenas os últimos 10 pontos após o filtro
            rows = rows[-10:]
        else:
            # Modo tolerante: usa as últimas 10 posições, independente de baseline
            cursor.execute(
                """
                SELECT ST_Y(LOCLATLONG) as lat, ST_X(LOCLATLONG) as lon, DATAHORA as ts
                FROM localizacao
                WHERE FK_VEICOD = %s
                ORDER BY DATAHORA DESC
                LIMIT 10
                """,
                (veicod,),
            )
            rows = cursor.fetchall()
            # inverter para ordem cronológica crescente
            rows = list(reversed(rows))
        progress[did] = len(rows)
        if len(rows) < 10:
            # continua acumulando progresso para todos os dispositivos
            continue
        route_name = expected_route_name_for_device(did)
        route = ROUTES[route_name]
        # checar e acumular dados para relatório
        pts_info = []
        for r in rows:  # já em ordem cronológica
            lat, lon = r['lat'], r['lon']
            if not is_point_on_route(lat, lon, route):
                return False, {}
            idx, (plat, plon), ddeg, dmeters = closest_route_point(lat, lon, route)
            pts_info.append({
                'lat': lat, 'lon': lon,
                'route_index': idx,
                'route_lat': plat, 'route_lon': plon,
                'dist_m': round(dmeters, 2)
            })
        report_data[did] = {
            'veicod': veicod,
            'route_name': route_name,
            'points': pts_info,
        }
    # sucesso somente se todos possuírem 10 pontos
    if len(report_data) == len(SIMULATOR_IDS) and all(progress.get(did, 0) >= 10 for did in SIMULATOR_IDS):
        return True, report_data, progress
    return False, report_data, progress


def write_report(data: dict):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"TESTE_{ts}.md"
    lines = []
    lines.append(f"# Relatório de Verificação de Rotas — {ts}")
    lines.append("")
    lines.append("Todos os veículos possuem 10 pontos pertencentes às rotas esperadas.")
    lines.append("")
    for did in sorted(data.keys()):
        info = data[did]
        lines.append(f"## Veículo {did} (VEICOD {info['veicod']}) — Rota: {info['route_name']}")
        for i, p in enumerate(info['points'], 1):
            lines.append(
                f"- P{i:02d}: ({p['lat']:.5f}, {p['lon']:.5f}) -> rota[{p['route_index']}] "
                f"({p['route_lat']:.5f}, {p['route_lon']:.5f}), dist≈{p['dist_m']} m"
            )
        lines.append("")
    with open(fname, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Relatório gerado: {fname}")


def main():
    deadline = time.time() + 300  # 5 min
    global BASELINE
    while time.time() < deadline:
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                if BASELINE is None:
                    BASELINE = fetch_baseline(conn)
                ok, data, prog = check_all(conn)
                if ok:
                    # Imprime um snapshot final de progresso, mesmo em sucesso imediato
                    summary = ", ".join(f"{k}:{prog.get(k,0)}" for k in SIMULATOR_IDS)
                    label = "novos/10" if STRICT_MODE else "coletados/10"
                    print(f"Progresso final ({label}): {summary}")
                    print("STATUS: SUCESSO")
                    write_report(data)
                    return
                # feedback de progresso resumido
                summary = ", ".join(f"{k}:{prog.get(k,0)}" for k in SIMULATOR_IDS)
                label = "novos/10" if STRICT_MODE else "coletados/10"
                print(f"Progresso ({label}): {summary}")
        except mysql.connector.Error as err:
            print(f"DB ERRO: {err}")
        time.sleep(5)
    print("STATUS: FALHA")


if __name__ == "__main__":
    main()
