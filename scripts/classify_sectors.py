#!/usr/bin/env python3
"""Label the works the keyword rules could not, and cache the answers.

Deliberately separate from the scoring run. Scoring stays offline,
deterministic and free; this is the one step that talks to a model, and you
choose when to run it. It is resumable - every batch is written to the cache as
it lands, so a rate limit or a Ctrl-C costs you the current batch and nothing
else.

    export GEMINI_API_KEY=...
    python3 scripts/classify_sectors.py --limit 300     # try it on 300 first
    python3 scripts/classify_sectors.py                 # the rest

The free tier is Flash-only at 10-15 requests a minute and 100-1,000 a day, so
a full pass over 42,098 descriptions is ~281 requests and may need to be run
across two days. Re-running is safe and cheap: cached descriptions are skipped.
"""

import argparse
import functools
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "data"))

import psycopg2  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

import llm_sectors  # noqa: E402

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")


def unclassified_descriptions(limit=None, cache=None):
    """Descriptions the keyword rules cannot label and the cache has not answered.

    Read from `projects` rather than `project_scores`, so this does not depend
    on scoring having run. That dependency was real cost: it forced the nightly
    order to be load -> score -> classify, which left every new label unused
    until the following night, and the join it needed (p.id = s.project_id)
    silently broke when scores were rekeyed on work_key.

    Commonest first, so a partial run buys the most works per request. The
    cache is subtracted BEFORE `limit` is applied: a description the model has
    already answered "Other" for is indistinguishable in the data from one it
    has never seen, so limiting first meant re-asking the same answered rows
    forever and reporting "0 newly labelled".
    """
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT description, COUNT(*) AS works
                FROM projects WHERE description IS NOT NULL
                GROUP BY description ORDER BY works DESC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    from sectors import classify_sector, normalize

    cache = cache if cache is not None else {}
    pending = []
    for description, works in rows:
        key = normalize(description)
        if not key or key in cache:
            continue
        if classify_sector(description) != llm_sectors.OTHER:
            continue
        pending.append((description, works))
    return pending[:limit] if limit else pending


def main():
    # Redirected to a file, Python block-buffers stdout, so a long run looks
    # dead until it exits. Every progress line here is a heartbeat; flush it.
    global print
    print = functools.partial(__builtins__.print if not isinstance(__builtins__, dict)
                              else __builtins__["print"], flush=True)

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the N commonest descriptions")
    ap.add_argument("--batch-size", type=int, default=llm_sectors.BATCH_SIZE)
    ap.add_argument("--model", default=llm_sectors.MODEL)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be sent, call nothing")
    args = ap.parse_args()

    cache = llm_sectors.load_cache()
    rows = unclassified_descriptions(args.limit, cache)
    descriptions = [d for d, _ in rows]
    works = sum(n for _, n in rows)
    print(f"{len(descriptions):,} unanswered descriptions covering {works:,} works; "
          f"{len(cache):,} already cached")

    if args.dry_run:
        pending = llm_sectors.classify_missing(descriptions, client=None, cache=cache,
                                               progress=lambda *_: None)
        # classify_missing returns {} without a client, so count the work here.
        from sectors import classify_sector, normalize
        todo = {normalize(d) for d in descriptions
                if classify_sector(d) == llm_sectors.OTHER and normalize(d)
                and normalize(d) not in cache}
        calls = -(-len(todo) // args.batch_size)
        print(f"dry run: {len(todo):,} to classify, ~{calls} requests "
              f"at {args.batch_size} per request")
        return 0

    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set - nothing to do. Get a free key at "
              "https://aistudio.google.com/apikey")
        return 1

    client = llm_sectors.GeminiClassifier(model=args.model)
    print(f"model: {args.model}")

    # Written after every batch rather than at the end: a run that dies to a
    # daily quota keeps everything it already paid for.
    def flush(fresh):
        if fresh:
            cache.update(fresh)
            llm_sectors.save_cache(cache)

    total_new = 0
    remaining = [d for d in descriptions]
    while remaining:
        head, remaining = remaining[:args.batch_size], remaining[args.batch_size:]
        # Never silence this: classify_missing reports a failed batch through
        # `progress`, and swallowing it made a run that labelled nothing look
        # like a run that found nothing to do.
        fresh = llm_sectors.classify_missing(head, client=client, cache=cache,
                                             batch_size=args.batch_size,
                                             progress=print)
        flush(fresh)
        total_new += len(fresh)
        print(f"  cached {len(cache):,} descriptions "
              f"(+{len(fresh)} this batch, {len(remaining):,} to go)")
        if llm_sectors.QUOTA_EXHAUSTED:
            print("  daily free-tier quota reached - stopping. Re-run tomorrow; "
                  "everything classified so far is cached.")
            break

    print(f"\ndone: {total_new:,} newly labelled, {len(cache):,} cached in total")
    if total_new:
        print("Run data/scoring.py to fold them into the peer groups.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
