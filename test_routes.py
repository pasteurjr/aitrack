import mysql.connector
import math

# Configurações e dados replicados do nosso ambiente
DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}

ROUTES = {
    "908T-10": [(-23.5505, -46.6333), (-23.5510, -46.6345), (-23.5520, -46.6360), (-23.5535, -46.6380), (-23.5550, -46.6400)],
    "8700-10": [(-23.5610, -46.6550), (-23.5600, -46.6570), (-23.5590, -46.6590), (-23.5580, -46.6610), (-23.5570, -46.6630)],
    "5111-10": [(-23.6820, -46.6960), (-23.6800, -46.6955), (-23.6780, -46.6950), (-23.6760, -46.6945), (-23.6740, -46.6940)],
    "175T-10": [(-23.4960, -46.6290), (-23.4970, -46.6310), (-23.4980, -46.6330), (-23.4990, -46.6350), (-23.5000, -46.6370)],
    "647A-10": [(-23.6100, -46.7000), (-23.6110, -46.6980), (-23.6120, -46.6960), (-23.6130, -46.6940), (-23.6140, -46.6920)]
}

SIMULATOR_IDS = [f"SIM-{1000 + i}" for i in range(10)]

# Tolerância para a comparação de coordenadas
TOLERANCE = 0.001 # Aprox. 111 metros

def is_point_on_route(point, route_coords):
    """Verifica se um ponto está próximo de qualquer ponto em uma rota."""
    for route_point in route_coords:
        dist = math.sqrt((point['latitude'] - route_point[0])**2 + (point['longitude'] - route_point[1])**2)
        if dist <= TOLERANCE:
            return True
    return False

def run_test():
    report = []
    conn = None
    all_tests_passed = True
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        route_names = list(ROUTES.keys())

        for i, device_id in enumerate(SIMULATOR_IDS):
            assigned_route_name = route_names[i % len(route_names)]
            assigned_route_coords = ROUTES[assigned_route_name]
            
            report.append(f"### Teste para Veículo: `{device_id}` (Rota: {assigned_route_name})\n")

            # Busca o VEICOD para o device_id
            cursor.execute("SELECT VEICOD FROM veiculos WHERE VEI_DEVICE_ID = %s", (device_id,))
            vehicle = cursor.fetchone()

            if not vehicle:
                report.append("- **Resultado:** <font color='red'>FALHA</font>")
                report.append("- **Motivo:** Veículo não encontrado no banco de dados.\n")
                all_tests_passed = False
                continue

            vehicle_id_db = vehicle['VEICOD']

            # Busca as últimas 10 posições
            cursor.execute("""
                SELECT ST_Y(LOCLATLONG) as latitude, ST_X(LOCLATLONG) as longitude 
                FROM localizacao 
                WHERE FK_VEICOD = %s 
                ORDER BY DATAHORA DESC 
                LIMIT 10
            """, (vehicle_id_db,))
            positions = cursor.fetchall()

            if len(positions) < 5: # Exige um mínimo de 5 pontos para um teste válido
                report.append("- **Resultado:** <font color='orange'>INCONCLUSIVO</font>")
                report.append(f"- **Motivo:** Poucos pontos encontrados ({len(positions)}/10). O simulador precisa rodar por mais tempo.\n")
                all_tests_passed = False
                continue

            report.append(f"- **DEBUG:** Rota esperada: {assigned_route_name}")
            report.append(f"- **DEBUG:** Coordenadas da rota: {assigned_route_coords}")
            report.append(f"- **DEBUG:** Posições encontradas no BD: {positions}")

            # Verifica se cada ponto pertence à rota designada
            match_count = 0
            for pos in positions:
                if is_point_on_route(pos, assigned_route_coords):
                    match_count += 1
            
            if match_count == len(positions):
                report.append("- **Resultado:** <font color='green'>SUCESSO</font>")
                report.append(f"- **Detalhes:** {match_count} de {len(positions)} pontos correspondem à rota designada.\n")
            else:
                report.append("- **Resultado:** <font color='red'>FALHA</font>")
                report.append(f"- **Detalhes:** Apenas {match_count} de {len(positions)} pontos correspondem à rota. Os dados estão misturados.\n")
                all_tests_passed = False

    except mysql.connector.Error as err:
        report.append("# ERRO GERAL DO TESTE\n")
        report.append(f"Falha ao conectar ou executar query no banco: {err}")
        all_tests_passed = False
    finally:
        if conn:
            conn.close()

    # Escreve o relatório
    with open("TEST_RESULTS.md", "w") as f:
        f.write("# Relatório de Verificação de Rotas\n\n")
        if all_tests_passed:
            f.write("## <font color='green'>Status Geral: SUCESSO</font>\n")
            f.write("Todos os 10 veículos estão seguindo suas rotas corretamente.\n\n")
        else:
            f.write("## <font color='red'>Status Geral: FALHA</font>\n")
            f.write("Um ou mais veículos não estão seguindo suas rotas. Análise detalhada abaixo.\n\n")
        f.write("---\n")
        f.write("\n".join(report))
    
    print("Relatório de teste gerado em TEST_RESULTS.md")

if __name__ == "__main__":
    run_test()
