import os
import threading
import time
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
                    # One, opened by the request that builds the pool; three
                    # more are opened behind it by _warm (below).
                    minconn=1,
                    # Fluid Compute reuses one instance across concurrent
                    # requests, so a handful of connections covers it; Neon's
                    # pooled endpoint caps well above this. 16 rather than 8
                    # since /api/alerts began running its rows and its total at
                    # the same time: two per request, and a build prerenders
                    # seven pages at once, which exhausted a pool of 8 and
                    # failed the build with "connection pool exhausted".
                    maxconn=16,
                    dsn=os.environ["DATABASE_URL"],
                    cursor_factory=RealDictCursor,
                    # Keep the link warm and notice a dead one quickly rather
                    # than blocking on a statement that will never answer.
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                )
                # psycopg2 keeps at most `minconn` connections idle and CLOSES
                # any other on putconn - so at minconn=1 every statement run
                # beside another opened a fresh connection, every time. Raised
                # after construction because the constructor opens minconn
                # connections up front, in front of the first request.
                _pool.minconn = 4
                threading.Thread(target=_warm, args=(_pool, 3), daemon=True).start()
    return _pool


def _warm(pool, n):
    """Open n more connections in the background and put them in the pool.

    Opening one is the expensive part (and only minconn of them are kept, so
    minconn is raised to match - see _get_pool): a fresh TLS handshake to Neon measured
    1.0-3.7s from a laptop against 0.6s for a round trip on a connection that
    already exists (2026-09-20), and a page runs two or three statements at
    once, so a pool of one made every statement but the first pay it. They
    were opened in the pool's constructor at first, which put all four
    handshakes - against a database that may be waking up - in front of the
    first request, and a failure among them failed that request. Here a
    failure costs nothing: the connection is simply opened later, on demand.
    """
    held = []
    try:
        for _ in range(n):
            held.append(pool.getconn())
    except Exception:
        pass
    for conn in held:
        pool.putconn(conn)


# A connection that died in the pool, rather than a bad statement. Neon closes
# idle connections, and a long-running loader or a quiet night is enough to
# leave every pooled connection unusable.
_STALE = (psycopg2.OperationalError, psycopg2.InterfaceError)


def _borrow(pool, wait=5.0):
    """Take a connection, waiting briefly rather than failing outright.

    psycopg2's pool raises the moment it is empty. A burst - a build
    prerendering seven pages at once, each page several endpoints - then turns
    into 500s even though the connections would free up milliseconds later.
    Queueing for a few seconds is what a caller wants; failing after that is
    still better than hanging forever.
    """
    deadline = time.monotonic() + wait
    while True:
        try:
            return pool.getconn()
        except pg_pool.PoolError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def _run(sql, params, fetch, commit):
    """Borrow a connection, run one statement, and hand it back.

    psycopg2's pool never checks whether a connection is still alive, and
    putconn would return a dead one for the next request to trip over - so a
    single expired connection becomes a rolling outage rather than one failed
    request. A stale connection is therefore closed instead of pooled, and the
    call is retried against the next one, until a live one answers.

    The retry is safe for the two statements that write: a decision is an
    upsert keyed on work_key and clearing one is a DELETE by work_key, so
    running either twice leaves the same state. (A retry happens only when the
    connection died, which is before the statement could commit.) Do not add a
    non-idempotent write without revisiting this.
    """
    pool = _get_pool()
    last = None
    # One more try than the pool keeps idle. Neon closes idle connections
    # together, so after a quiet spell every pooled one is dead at once; with a
    # single retry the second dead one failed the request (measured
    # 2026-09-21, "SSL connection has been closed unexpectedly" on the first
    # request after idling). Each dead one is discarded, so this ends at a
    # fresh connection.
    attempts = pool.minconn + 1
    for attempt in range(attempts):
        conn = _borrow(pool)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
                result = (cur.fetchone() if fetch == "one" else
                          cur.fetchall() if fetch == "all" else None)
            if commit:
                conn.commit()
            else:
                # A read still opens a transaction, and psycopg2 leaves it
                # open: the connection goes back to the pool "idle in
                # transaction", holding a snapshot and inviting the server to
                # cut it off, after which the next borrower pays for a new
                # connection. End it here.
                conn.rollback()
            pool.putconn(conn)
            return result
        except _STALE as err:
            # Unusable, not merely errored: drop it rather than pool it.
            pool.putconn(conn, close=True)
            last = err
            if attempt == attempts - 1:
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
