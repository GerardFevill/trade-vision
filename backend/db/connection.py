"""Database connection management"""
import os
import psycopg2
from contextlib import contextmanager

# Configuration PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'mt5monitor'),
    'user': os.getenv('POSTGRES_USER', 'mt5user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'mt5password'),
}


@contextmanager
def get_connection():
    """Context manager pour les connexions PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
