"""Load the real MPLADS CSV extracts into the `projects` table.

Source: the four CSVs in MPLADS_DATA_DIR, pulled from the public MPLADS portal
via scripts/fetch_mplads.py. Every row written here gets source='real'.

UNION, NOT JOIN
---------------
Recommended works (123,146) and completed works (124,353) across both Lok Sabha
terms share only 611 works, so they are two near-disjoint populations, not two
ends of one lifecycle. The
table is therefore a union: one row per recommended work (work_status
'recommended') plus one row per completed work (work_status 'completed'). Where a
Work ID appears in both, only the completed row is kept and the recommendation
date is recovered onto it as start_date.

THE ONE ASSUMPTION WE INVENT: expected_completion
-------------------------------------------------
The source data has no expected/target completion date, but delay_days and the
delay risk rule need one. We derive it as **start date + 365 days**, following
the MPLADS guideline that a sanctioned work is expected to be executed within a
year of recommendation.

  * recommended works -> Recommendation Date + 365d.
  * completed works with a recoverable recommendation date (the 611 shared
    works) -> Recommendation Date + 365d.
  * every other completed work -> NULL.

We deliberately do NOT derive it backwards from the completion date (e.g.
Completed Date - 365d): that would make delay_days identically zero for 43k rows
and dress up a fabricated number as a measurement. scoring.py's
compute_delay_days returns 0 when expected_completion is NaT, so a NULL means "we
cannot know this work's timeline, so it scores no delay risk" - honest, and it
still trips the compliance rule for a missing expected completion date.

EXPENDITURE
-----------
The expenditures CSV has no Work ID, so the only available join key would be
(MP Name, Work Description). That doesn't work: the expenditures file's "Work
Description" holds one of just 119 MPLADS *category labels* ("Construction of
roads, link roads, pathways...") across 270,934 rows, not a per-work
description, so joining on it matched under 1% of works, all coincidentally.
We don't join it at all.

Instead: for a completed work, its Final Amount IS what it cost, so
expenditure = sanctioned_amount (= Final Amount) for completed works.
Recommended/pending works have nothing recorded as spent yet, so
expenditure = 0. The expenditures CSV stays on disk for later vendor-level
analysis, just not joined per-work here.
"""

import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATA_DIR = Path(os.environ.get("MPLADS_DATA_DIR", "/home/rvina/projects/SIH HACKATHON/MPLADS DATA"))


def _newest(pattern):
    """Newest CSV matching the pattern, by the date in its filename.

    Snapshots are named mplads_<kind>_YYYY-MM-DD.csv. Pinning an exact date
    would make a scheduled refresh fail the moment a newer snapshot lands, so
    resolve the latest one instead. Sorting lexically is safe: ISO dates sort
    chronologically.
    """
    matches = sorted(DATA_DIR.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No file matching {pattern!r} in {DATA_DIR}. "
            "Set MPLADS_DATA_DIR to the directory holding the MPLADS CSV snapshots."
        )
    return matches[-1]


RECOMMENDED_CSV = _newest("mplads_recommended_works_*.csv")
COMPLETED_CSV = _newest("mplads_completed_works_*.csv")

EXPECTED_DURATION_DAYS = 365
# Amounts below this are data-entry noise, not works: the source has 39 rows
# under Rs 1,000 (down to Rs 1), and no civil work MPLADS funds can be executed
# for three figures. The real distribution starts around Rs 8,000 (25th
# percentile Rs 2 lakh), so the floor cuts only the junk tail.
MIN_SANCTIONED_AMOUNT = 1000

INSERT_COLUMNS = [
    "work_name", "description", "mp_name", "constituency", "state", "district",
    "category", "implementing_agency", "recommended_amount", "sanctioned_amount",
    "expenditure", "work_status", "start_date", "expected_completion",
    "actual_completion", "source", "has_images",
]


def parse_district(ida):
    """District is the IDA prefix before the first '(' - e.g.
    'CHITTOOR(DISTRICT COLLECTOR CHITTOOR_IDA)' -> 'CHITTOOR'."""
    return str(ida).split("(", 1)[0].strip().upper() or str(ida).strip().upper()


def to_date(series):
    return pd.to_datetime(series, format="ISO8601", errors="coerce", utc=True).dt.date


def work_key(df):
    """A work's identity is (Work ID, ls_term), not Work ID alone.

    Work IDs restart per Lok Sabha term: 9,862 completed Work IDs appear in both
    the 17th and 18th term extracts as different works. Matching on Work ID
    alone finds 804 shared IDs between recommended and completed, of which only
    611 are real - the other 193 are two unrelated works that happen to share a
    number across terms, and would silently take each other's start date.

    Snapshots taken before the ls_term column existed hold one term only, so
    treat a missing column as a single term and keep their behaviour unchanged.
    """
    term = df["ls_term"].astype(str) if "ls_term" in df.columns else "0"
    return df["Work ID"].astype(str) + "|" + pd.Series(term, index=df.index).astype(str)


def build_rows():
    """Return (rows_df, rejects) where rejects is a list of (raw_row, reason, file)."""
    rec = pd.read_csv(RECOMMENDED_CSV)
    com = pd.read_csv(COMPLETED_CSV)

    # Works present in both files: keep only the completed row, but carry the
    # recommendation date over as its start date.
    rec_key = work_key(rec)
    com_key = work_key(com)
    rec_date = to_date(rec["Recommendation Date"])
    shared = pd.Series(rec_date.values, index=rec_key).groupby(level=0).first()
    shared = shared[shared.index.isin(set(com_key))]
    rec = rec[~rec_key.isin(shared.index)].copy()
    rec["start_date"] = to_date(rec["Recommendation Date"])

    com = com.copy()
    com["start_date"] = com_key.map(shared)
    com["actual_completion"] = to_date(com["Completed Date"])

    rec["work_status"] = "recommended"
    rec["actual_completion"] = None
    rec["amount"] = rec["Recommended Amount (₹)"]
    com["work_status"] = "completed"
    com["amount"] = com["Final Amount (₹)"]

    keep = {"Work Description": "description", "Category": "category", "MP Name": "mp_name",
            "Constituency": "constituency", "State": "state", "IDA": "implementing_agency",
            "amount": "amount", "work_status": "work_status", "start_date": "start_date",
            "actual_completion": "actual_completion", "Has Images": "has_images"}
    df = pd.concat(
        [rec[list(keep)].rename(columns=keep), com[list(keep)].rename(columns=keep)],
        ignore_index=True,
    )
    df["source_file"] = [RECOMMENDED_CSV.name] * len(rec) + [COMPLETED_CSV.name] * len(com)

    amount = pd.to_numeric(df["amount"], errors="coerce")
    desc = df["description"].astype("string").str.strip()
    state = df["state"].astype("string").str.strip()
    blank = lambda s: (s.isna() | (s == "")).fillna(True)

    reason = pd.Series(pd.NA, index=df.index, dtype="string")
    reason = reason.mask(blank(state), "Missing state")
    reason = reason.mask(blank(desc), "Missing or empty work description")
    reason = reason.mask(amount.isna(), "Missing or non-numeric sanctioned amount")
    reason = reason.mask((amount <= 0).fillna(False), "Sanctioned amount is not positive")
    reason = reason.mask(((amount > 0) & (amount < MIN_SANCTIONED_AMOUNT)).fillna(False),
                         f"Sanctioned amount below Rs {MIN_SANCTIONED_AMOUNT} floor")

    ok = reason.isna()
    rejects = [
        (Json({k: (None if pd.isna(v) else str(v)) for k, v in row.items() if k != "source_file"}),
         str(reason[i]), row["source_file"])
        for i, row in df[~ok].iterrows()
    ]

    df = df[ok].copy()
    df["amount"] = amount[ok].astype(float)
    df["description"] = desc[ok].astype(str)

    # A completed work's Final Amount IS its expenditure; recommended works have
    # nothing recorded as spent yet.
    df["expenditure"] = df["amount"].where(df["work_status"] == "completed", 0.0)

    df["start_date"] = [None if pd.isna(d) else d for d in df["start_date"]]
    df["expected_completion"] = [
        None if d is None else d + pd.Timedelta(days=EXPECTED_DURATION_DAYS)
        for d in df["start_date"]
    ]
    df["actual_completion"] = [None if pd.isna(d) else d for d in df["actual_completion"]]
    # Has Images arrives as a plain bool column with no NaN in the source CSVs,
    # but treat missing/non-boolean values as unknown (SQL NULL) rather than
    # silently coercing them to False - absent information isn't a recorded
    # absence of images.
    df["has_images"] = [None if pd.isna(v) else bool(v) for v in df["has_images"]]
    df["district"] = df["implementing_agency"].map(parse_district)
    df["category"] = df["category"].fillna("Unknown")
    return df, rejects


def start_refresh_run(conn, source):
    """Insert a 'running' data_refresh row and return its id, or None on any
    failure. Audit bookkeeping must never block the pipeline itself."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO data_refresh (status, source) VALUES ('running', %s) RETURNING id",
                [source],
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id
    except Exception as e:  # noqa: BLE001 - audit trail is best-effort
        print(f"data_refresh: failed to insert running row: {e}")
        conn.rollback()
        return None


def finish_load_run(conn, run_id, status, rows_loaded, rows_rejected):
    if run_id is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE data_refresh
                   SET finished_at = now(), status = %s, rows_loaded = %s, rows_rejected = %s
                   WHERE id = %s""",
                [status, rows_loaded, rows_rejected, run_id],
            )
        conn.commit()
    except Exception as e:  # noqa: BLE001
        print(f"data_refresh: failed to update run {run_id}: {e}")
        conn.rollback()


def load(conn, df, rejects):
    rows = [
        (
            r.description[:60], r.description, r.mp_name, r.constituency, r.state, r.district,
            r.category, r.implementing_agency, r.amount, r.amount, r.expenditure, r.work_status,
            r.start_date, r.expected_completion, r.actual_completion, "real", r.has_images,
        )
        for r in df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE source = 'real'")
        execute_values(
            cur,
            f"INSERT INTO projects ({', '.join(INSERT_COLUMNS)}) VALUES %s",
            rows,
            page_size=1000,
        )
        if rejects:
            execute_values(
                cur,
                "INSERT INTO rejected_rows (raw_row, reason, source_file) VALUES %s",
                rejects,
                page_size=1000,
            )
    conn.commit()
    return len(rows), len(rejects)


if __name__ == "__main__":
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    run_id = start_refresh_run(conn, source=f"{RECOMMENDED_CSV.name}, {COMPLETED_CSV.name}")
    try:
        df, rejects = build_rows()
        inserted, rejected = load(conn, df, rejects)
    except Exception:
        # Loader failed before scoring ever ran - the row stays honest as
        # 'failed' rather than parked at 'running' forever. scoring.py's own
        # bookkeeping is unaffected since it never finds this run to update.
        finish_load_run(conn, run_id, "failed", None, None)
        conn.close()
        raise
    # Still 'running': scoring.py finishes this same row once it completes.
    finish_load_run(conn, run_id, "running", inserted, rejected)
    conn.close()
    print(f"Inserted {inserted} real projects, rejected {rejected} rows.")
    print(f"Total expenditure (completed works' Final Amount): "
          f"Rs {df['expenditure'].sum():,.2f}")
