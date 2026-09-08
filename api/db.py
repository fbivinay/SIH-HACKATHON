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


# A connection that died in the pool, rather than a bad statement. Neon closes
# idle connections, and a long-running loader or a quiet night is enough to
# leave every pooled connection unusable.
_STALE = (psycopg2.OperationalError, psycopg2.InterfaceError)


def _run(sql, params, fetch, commit):
    """Borrow a connection, run one statement, and hand it back.

    psycopg2's pool never checks whether a connection is still alive, and
    putconn would return a dead one for the next request to trip over - so a
    single expired connection becomes a rolling outage rather than one failed
    request. A stale connection is therefore closed instead of pooled, and the
    call is retried once against a fresh one.

    The retry is safe for the one statement that writes: it is an upsert keyed
    on work_key, so running it twice leaves the same row. Do not add a
    non-idempotent write without revisiting this.
    """
    pool = _get_pool()
    last = None
    for attempt in (0, 1):
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
                result = (cur.fetchone() if fetch == "one" else
                          cur.fetchall() if fetch == "all" else None)
            if commit:
                conn.commit()
            pool.putconn(conn)
            return result
        except _STALE as err:
            # Unusable, not merely errored: drop it rather than pool it.
            pool.putconn(conn, close=True)
            last = err
            if attempt == 1:
                raise
        except Exception:
            # A real statement error. The connection is fine once the aborted
            # transaction is rolled back, so keep it.
            try:
                conn.rollback()
            except Exception:
                pass
            pool.putconn(conn)
            raise
    raise last  # unreachable; keeps the contract explicit


def query(sql, params=None, one=False):
    return _run(sql, params, "one" if one else "all", commit=False)


def execute(sql, params=None, returning=False):
    """Run a statement that writes, and commit it.

    Separate from query() rather than a flag on it: every caller of query() is
    a GET handler that must never be able to commit by accident.
    """
    return _run(sql, params, "one" if returning else None, commit=True)
