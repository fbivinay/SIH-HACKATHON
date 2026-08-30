import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def query(sql, params=None, one=False):
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()
