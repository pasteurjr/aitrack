import mysql.connector

DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}

def verify_data():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        print("\n--- Verificando dados para Maxtrack (SIM-1000) ---")
        cursor.execute("""
            SELECT l.DATAHORA, l.FK_VEICOD, v.VEI_DEVICE_ID, ST_Y(l.LOCLATLONG) as lat, ST_X(l.LOCLATLONG) as lon
            FROM localizacao l
            JOIN veiculos v ON l.FK_VEICOD = v.VEICOD
            WHERE v.VEI_DEVICE_ID = 'SIM-1000'
            ORDER BY l.DATAHORA DESC
            LIMIT 5
        """)
        results = cursor.fetchall()
        for row in results:
            print(row)

        print("\n--- Verificando dados para Suntech (SIM-1001) ---")
        cursor.execute("""
            SELECT l.DATAHORA, l.FK_VEICOD, v.VEI_DEVICE_ID, ST_Y(l.LOCLATLONG) as lat, ST_X(l.LOCLATLONG) as lon
            FROM localizacao l
            JOIN veiculos v ON l.FK_VEICOD = v.VEICOD
            WHERE v.VEI_DEVICE_ID = 'SIM-1001'
            ORDER BY l.DATAHORA DESC
            LIMIT 5
        """)
        results = cursor.fetchall()
        for row in results:
            print(row)

    except mysql.connector.Error as err:
        print(f"ERRO ao verificar o banco de dados: {err}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_data()
