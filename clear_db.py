import os
import mysql.connector

DB_CONFIG = {
    'host': os.environ['AITRACK_DB_HOST'],
    'port': int(os.getenv('AITRACK_DB_PORT', '3306')),
    'user': os.environ['AITRACK_DB_USER'],
    'password': os.environ['AITRACK_DB_PASSWORD'],
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
