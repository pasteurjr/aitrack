import mysql.connector

DB_CONFIG = {
    'host': 'camerascasas.no-ip.info',
    'port': 3307,
    'user': 'scadabr',
    'password': 'scadabr',
    'database': 'tracker'
}

def clear_location_table():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Limpando a tabela 'localizacao'...")
        cursor.execute("TRUNCATE TABLE localizacao")
        conn.commit()
        print("Tabela 'localizacao' limpa com sucesso.")
    except mysql.connector.Error as err:
        print(f"ERRO ao limpar o banco de dados: {err}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clear_location_table()
