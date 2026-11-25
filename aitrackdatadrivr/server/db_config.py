"""Configuração de banco exclusivamente por ambiente; nenhum fallback de credencial."""

import os

from .env_loader import load_dotenv


def database_config(database=None):
    load_dotenv()
    required = ('AITRACK_DB_HOST', 'AITRACK_DB_USER', 'AITRACK_DB_PASSWORD')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError('Configuração de banco ausente: ' + ', '.join(missing))
    return {
        'host': os.environ['AITRACK_DB_HOST'],
        'port': int(os.getenv('AITRACK_DB_PORT', '3306')),
        'user': os.environ['AITRACK_DB_USER'],
        'password': os.environ['AITRACK_DB_PASSWORD'],
        'database': database or os.getenv('AITRACK_DB_NAME', 'tracker'),
    }
