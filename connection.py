import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

load_dotenv()


def get_mysql_connection() -> Connection:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = 3307
    user = os.getenv("MYSQL_USER", "appuser")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", "apppass"))
    database = os.getenv("MYSQL_DATABASE", "mysql_db")

    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
        future=True,
    )
    return engine.connect()
