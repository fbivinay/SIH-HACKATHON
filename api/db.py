import os
import threading
from pathlib import Path
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Opening a fresh connection per request costs ~1.2s against remote Neon (TLS
# handshake + auth), which dwarfed the queries themselves (~0.2-0.4s) and made
# every page feel slow. A small pool amortises that away.
#
# Built lazily rather than at import time so the module still imports when
# DATABASE_URL is absent (tests collecting, a build step) and so a serverless
# cold start pays for the pool only on its first real request.
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pg_pool.ThreadedConnectionPool(
                    minconn=1,
                    # Fluid Compute reuses one instance across concurrent
                    # requests, so a handful of connections covers it; Neon's
                    # pooled endpoint caps well above this.
                    maxconn=8,
                    dsn=os.environ["DATABASE_URL"],
                    cursor_factory=RealDictCursor,
                )
    return _pool


def query(sql, params=None, one=False):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchone() if one else cur.fetchall()
    except Exception:
        # A connection that errored may be in an unusable transaction state;
        # roll back before returning it so the next borrower gets it clean.
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        pool.putconn(conn)
