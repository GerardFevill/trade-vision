"""Database connection management with connection pooling"""
from contextlib import contextmanager
from typing import Optional
import psycopg2
from psycopg2 import pool
from config.settings import settings
from config.logging import logger

# Global connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_pool():
    """Initialize the connection pool"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=settings.postgres_pool_min,
                maxconn=settings.postgres_pool_max,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
            )
            logger.info(
                "Database connection pool initialized",
                min_connections=settings.postgres_pool_min,
                max_connections=settings.postgres_pool_max,
                host=settings.postgres_host,
                database=settings.postgres_db
            )
        except Exception as e:
            logger.error("Failed to initialize connection pool", error=str(e))
            raise


def close_pool():
    """Close the connection pool"""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed")


@contextmanager
def get_connection():
    """Context manager for pooled PostgreSQL connections"""
    global _connection_pool

    # Initialize pool if needed
    if _connection_pool is None:
        init_pool()

    conn = None
    try:
        conn = _connection_pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Database operation failed", error=str(e))
        raise
    finally:
        if conn:
            _connection_pool.putconn(conn)


# Legacy configuration for backward compatibility
DB_CONFIG = {
    'host': settings.postgres_host,
    'port': settings.postgres_port,
    'database': settings.postgres_db,
    'user': settings.postgres_user,
    'password': settings.postgres_password,
}
