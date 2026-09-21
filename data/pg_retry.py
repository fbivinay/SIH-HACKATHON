"""Retry a nightly write that lost a lock fight with the live site.

The refresh rewrites whole tables while the deployed site keeps reading them.
A write that takes exclusive locks on two relations in turn can deadlock with
a single ordinary read that locked them in the other order - a visitor's query
on the projects_scored view holds the view and waits for projects while the
write holds projects and waits for the view. Postgres resolves that by
cancelling one of them; on 2026-09-20 it cancelled the refresh, and the night's
data never landed (DeadlockDetected in the schema step).

Nothing about the write was wrong, only its timing, so it is retried: rolled
back, a pause, and again. Every write wrapped here is a whole transaction that
replaces what it touches, so running it twice leaves the same result.
lock_timeout makes a write that cannot get its lock give up after 10s instead
of queueing - a queued exclusive lock also stalls every reader behind it, so
the site would hang for as long as the write waited.
"""

import time

from psycopg2 import errors

RETRYABLE = (errors.DeadlockDetected, errors.LockNotAvailable)


def with_lock_retry(conn, fn, *args, attempts=6, label="write", **kwargs):
    delay = 5
    for attempt in range(1, attempts + 1):
        try:
            with conn.cursor() as cur:
                # Inside the attempt's own transaction, so a rollback cannot
                # leave it behind for the next statement to inherit oddly.
                cur.execute("SET lock_timeout = '10s'")
            return fn(conn, *args, **kwargs)
        except RETRYABLE as err:
            conn.rollback()
            if attempt == attempts:
                raise
            print(
                f"{label}: {type(err).__name__} against a concurrent reader "
                f"(attempt {attempt} of {attempts}) - retrying in {delay}s"
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)


if __name__ == "__main__":
    # The retry logic, without a database: a function that deadlocks twice and
    # then succeeds must be called three times and return its value.
    class FakeConn:
        rollbacks = 0

        def cursor(self):
            class C:
                def __enter__(s):
                    return s

                def __exit__(s, *a):
                    return False

                def execute(s, *a):
                    pass

            return C()

        def rollback(self):
            FakeConn.rollbacks += 1

    calls = []

    def flaky(conn):
        calls.append(1)
        if len(calls) < 3:
            raise errors.DeadlockDetected("deadlock detected")
        return "done"

    import pg_retry

    pg_retry.time.sleep = lambda s: None
    assert with_lock_retry(FakeConn(), flaky, label="test") == "done"
    assert len(calls) == 3 and FakeConn.rollbacks == 2
    print("pg_retry self-check passed")
