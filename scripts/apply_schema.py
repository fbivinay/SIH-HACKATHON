"""Apply data/schema.sql - only when it has changed, and retried on a lock fight.

schema.sql is re-runnable, and the nightly refresh used to run all of it every
night. That is not free: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and its
kind take an exclusive lock on the table even when there is nothing to add,
and the file does so for several tables in one transaction. On 2026-09-20 that
deadlocked with one visitor's query on the projects_scored view and the whole
refresh failed.

So the file's hash is recorded once it has been applied, and a night whose
schema.sql is the one already applied takes no locks at all. When it has
changed, it is applied inside data/pg_retry.py, which retries a deadlock.
SCHEMA_FORCE=1 applies it regardless.
"""

import hashlib
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from pg_retry import with_lock_retry  # noqa: E402

SCHEMA = ROOT / "data" / "schema.sql"


def main():
    sql = SCHEMA.read_text()
    sha = hashlib.sha256(sql.encode()).hexdigest()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    # Its own table and nothing else, so creating it cannot contend with the
    # site's readers.
    with conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_applied "
            "(sha256 TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute("SELECT 1 FROM schema_applied WHERE sha256 = %s", [sha])
        applied = cur.fetchone() is not None
    if applied and os.environ.get("SCHEMA_FORCE") != "1":
        print(f"schema unchanged ({sha[:12]}) - nothing applied, no locks taken")
        conn.close()
        return

    def apply(c):
        with c.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_applied (sha256) VALUES (%s) ON CONFLICT DO NOTHING", [sha]
            )
        c.commit()

    with_lock_retry(conn, apply, label="apply schema")
    conn.close()
    print(f"schema applied ({sha[:12]})")


if __name__ == "__main__":
    main()
