import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

load_dotenv()


def get_mysql_engine() -> Engine:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3307"))
    user = os.getenv("MYSQL_USER", "appuser")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", "apppass"))
    database = os.getenv("MYSQL_DATABASE", "mysql_db")

    return create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
        future=True,
    )

def get_mysql_connection() -> Connection:
    return get_mysql_engine().connect()


def get_postgres_engine() -> Engine:
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "appuser")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "apppass"))
    database = os.getenv("POSTGRES_DB") or os.getenv("POSTGRES_DATABASE", "pg_db")

    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
        future=True,
    )


def get_postgres_connection() -> Connection:
    return get_postgres_engine().connect()
