"""
database.py — PostgreSQL connection pool + schema initializer
"""
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "retail_db")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT     = os.getenv("DB_PORT", "5432")

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
    return _pool


def get_connection():
    return _get_pool().getconn()


def release_connection(conn):
    _get_pool().putconn(conn)


def init_db():
    """Run schema.sql against the database (idempotent — uses IF NOT EXISTS)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    with open(schema_path, "r") as f:
        sql = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)


def execute_query(query: str, params=None, fetch: bool = False):
    """Generic query executor using a RealDictCursor."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            result = cur.fetchall() if fetch else None
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)
