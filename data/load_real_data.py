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

from mps import safe_mp_key

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


def _newest_optional(pattern):
    """Like _newest, but returns None instead of raising.

    The 2026-08-30 snapshot shipped only the two work-level CSVs, so an older
    snapshot legitimately has no expenditure file. Missing it should cost the
    vendor signal, not the whole load.
    """
    try:
        return _newest(pattern)
    except FileNotFoundError:
        return None


RECOMMENDED_CSV = _newest("mplads_recommended_works_*.csv")
COMPLETED_CSV = _newest("mplads_completed_works_*.csv")
EXPENDITURES_CSV = _newest_optional("mplads_expenditures_*.csv")
MP_SUMMARY_CSV = _newest_optional("mplads_mp_summary_*.csv")

EXPECTED_DURATION_DAYS = 365
# Amounts below this are data-entry noise, not works: the source has 39 rows
# under Rs 1,000 (down to Rs 1), and no civil work MPLADS funds can be executed
# for three figures. The real distribution starts around Rs 8,000 (25th
# percentile Rs 2 lakh), so the floor cuts only the junk tail.
MIN_SANCTIONED_AMOUNT = 1000

# What `projects` holds: the source's own fields and nothing derived.
#
# `sector` is not here, and its absence broke every nightly refresh for two
# days. It was moved to project_scores with the rest of the derived columns,
# and the loader kept computing and inserting it - a column the table no longer
# had. Scoring recomputes it from the description on every run, so the loader
# does not need it at all.
INSERT_COLUMNS = [
    "work_key", "work_name", "description", "ls_term", "mp_name", "mp_id", "house",
    "constituency", "state", "district",
    "category", "implementing_agency", "recommended_amount",
    "sanctioned_amount", "expenditure", "work_status", "start_date",
    "expected_completion", "actual_completion", "source", "has_images",
]


def parse_district(ida):
    """District is the IDA prefix before the first '(' - e.g.
    'CHITTOOR(DISTRICT COLLECTOR CHITTOOR_IDA)' -> 'CHITTOOR'."""
    return str(ida).split("(", 1)[0].strip().upper() or str(ida).strip().upper()


def to_date(series):
    return pd.to_datetime(series, format="ISO8601", errors="coerce", utc=True).dt.date


def work_key(df):
    """A work's identity is (Work ID, ls_term, IDA). The agency is part of the
    key, not decoration.

    Work IDs restart per Lok Sabha term: 9,862 completed Work IDs appear in both
    the 17th and 18th term extracts as different works. But the term alone is
    not enough, because the numbering also restarts per implementing agency.
    Measured on the 2026-08-31 snapshot, keying on (Work ID, ls_term) alone:

      - 128 recommended keys name two unrelated works, in different states;
      - 611 completed works match a recommendation, but only 340 of those are
        in the same state. The other 271 took a stranger's recommendation date
        as their start_date, which feeds delay_days and a quarter of the score.

    Adding IDA makes the key unique in both extracts - 0 duplicates across
    123,146 recommended and 124,353 completed rows - and cuts the cross-file
    matches to 328, every one of them in the same state.

    Persisted as projects.work_key so a work keeps one identity across reloads:
    the loader deletes and re-inserts every real row, so the serial id does not
    survive a refresh and cannot anchor anything (see work_reviews).

    Snapshots taken before the ls_term column existed hold one term only, so
    treat a missing column as a single term and keep their behaviour unchanged.
    """
    term = df["ls_term"].astype(str) if "ls_term" in df.columns else "0"
    return (
        df["Work ID"].astype(str)
        + "|" + pd.Series(term, index=df.index).astype(str)
        + "|" + df["IDA"].astype(str).str.strip()
    )


def build_rows():
    """Return (rows_df, rejects) where rejects is a list of (raw_row, reason, file)."""
    rec = pd.read_csv(RECOMMENDED_CSV)
    com = pd.read_csv(COMPLETED_CSV)
    # Snapshots predating the column hold one term only; 0 marks "term unknown"
    # rather than silently claiming one of them.
    for frame in (rec, com):
        if "ls_term" not in frame.columns:
            frame["ls_term"] = 0

    # Works present in both files: keep only the completed row, but carry the
    # recommendation date over as its start date.
    rec_key = work_key(rec)
    com_key = work_key(com)
    rec_date = to_date(rec["Recommendation Date"])
    shared = pd.Series(rec_date.values, index=rec_key).groupby(level=0).first()
    shared = shared[shared.index.isin(set(com_key))]
    rec = rec[~rec_key.isin(shared.index)].copy()
    rec["start_date"] = to_date(rec["Recommendation Date"])
    rec["work_key"] = work_key(rec)

    com = com.copy()
    com["start_date"] = com_key.map(shared)
    com["work_key"] = com_key
    com["actual_completion"] = to_date(com["Completed Date"])

    rec["work_status"] = "recommended"
    rec["actual_completion"] = None
    rec["amount"] = rec["Recommended Amount (₹)"]
    com["work_status"] = "completed"
    com["amount"] = com["Final Amount (₹)"]

    keep = {"Work Description": "description", "Category": "category", "MP Name": "mp_name",
            "House": "house", "ls_term": "ls_term", "work_key": "work_key",
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
    # mp_name is not a key (see data/mps.py). safe_mp_key rather than mp_key:
    # a work whose MP name is unusable is still a work worth loading, it just
    # cannot take part in per-MP aggregates.
    df["mp_id"] = [
        safe_mp_key(n, st, h)
        for n, st, h in zip(df["mp_name"], df["state"], df["house"])
    ]
    return df, rejects


def start_refresh_run(conn, source):
    """Insert a 'running' data_refresh row and return its id, or None on any
    failure. Audit bookkeeping must never block the pipeline itself.

    Any earlier row still marked 'running' is closed first. A refresh that is
    killed rather than failed - a workflow timeout, a cancelled job, a runner
    that vanishes - never reaches finish_load_run, so its row sits at 'running'
    forever. Two things then go wrong: the freshness line keeps quoting the last
    successful run as if nothing had been attempted since, and scoring.py adopts
    the newest 'running' row, so the next pass stamps a stranger's abandoned
    record as its own success. The refresh workflow holds a concurrency group of
    one, so by the time a new load starts, any other 'running' row is abandoned
    by definition.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE data_refresh SET status = 'failed', finished_at = now(),
                       notes = COALESCE(notes || ' | ', '')
                              || 'abandoned: never finished, closed by a later run'
                   WHERE status = 'running'"""
            )
            if cur.rowcount:
                print(f"data_refresh: closed {cur.rowcount} abandoned run(s).")
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


def build_expenditure_rows():
    """Expenditure transactions, at their own grain.

    No join to works is attempted: the file carries no Work ID and its Work
    Description is one of 119 category labels, not a description (see the module
    docstring). Rows without a vendor, an agency or a positive amount are
    dropped rather than rejected into rejected_rows - that table is about works,
    and an unusable payment row is not a work we failed to load.
    """
    exp = pd.read_csv(EXPENDITURES_CSV)
    amount = pd.to_numeric(exp["Expenditure Amount (₹)"], errors="coerce")
    vendor = exp["Vendor"].astype("string").str.strip()
    agency = exp["IDA"].astype("string").str.strip()

    usable = amount.notna() & (amount > 0) & vendor.notna() & (vendor != "") & agency.notna() & (agency != "")
    exp = exp[usable].copy()
    out = pd.DataFrame({
        "ls_term": exp["ls_term"] if "ls_term" in exp.columns else None,
        "mp_name": exp["MP Name"],
        "constituency": exp["Constituency"],
        "state": exp["State"],
        "work_type_text": exp["Work Description"],
        "vendor": vendor[usable],
        "implementing_agency": agency[usable],
        "district": agency[usable].map(parse_district),
        "expenditure_amount": amount[usable].astype(float),
        "expenditure_date": to_date(exp["Expenditure Date"]),
        "payment_status": exp["Payment Status"],
    })
    return out, int((~usable).sum())


EXPENDITURE_COLUMNS = [
    "ls_term", "mp_name", "constituency", "state", "work_type_text", "vendor",
    "implementing_agency", "district", "expenditure_amount", "expenditure_date",
    "payment_status",
]


def load_expenditures(conn, df):
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df[EXPENDITURE_COLUMNS].itertuples(index=False, name=None)
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE expenditures RESTART IDENTITY")
        execute_values(
            cur,
            f"INSERT INTO expenditures ({', '.join(EXPENDITURE_COLUMNS)}) VALUES %s",
            rows,
            page_size=1000,
        )
    conn.commit()
    return len(rows)


MP_COLUMNS = [
    "mp_id", "ls_term", "mp_name", "constituency", "state", "house",
    "allocated_amount", "amount_recommended", "total_expenditure",
    "utilization_pct", "completed_works",
    "recommended_works", "completion_rate_pct", "unspent_amount",
    "transaction_count", "successful_payments", "pending_payments",
]

# The source renames columns between extracts. On 2026-09-09 "Unspent Amount"
# became "Balance Not Yet Paid to Vendors" - a better name for what it always
# was - and the load died on a KeyError after it had already committed the
# works, leaving the database holding a new snapshot's works beside the
# previous one's payments. Each field lists the spellings seen, newest first.
MP_SOURCE_COLUMNS = {
    "allocated_amount": ["Allocated Amount (₹)"],
    "amount_recommended": ["Amount Recommended (₹)"],
    "total_expenditure": ["Total Expenditure (₹)"],
    "utilization_pct": ["Utilization %"],
    "completed_works": ["Completed Works"],
    "recommended_works": ["Recommended Works"],
    "completion_rate_pct": ["Completion Rate %"],
    "unspent_amount": ["Balance Not Yet Paid to Vendors (₹)", "Unspent Amount (₹)"],
    "transaction_count": ["Transaction Count"],
    "successful_payments": ["Successful Payments"],
    "pending_payments": ["Pending Payments"],
}


def build_mp_rows():
    """The source's own per-MP-per-term aggregates.

    Loaded as published rather than recomputed from the works: these are the
    numbers Empowered Indian shows, so a utilisation figure in this dashboard
    can be checked against theirs.
    """
    mp = pd.read_csv(MP_SUMMARY_CSV)

    def num(field):
        """Read a numeric field by whichever spelling this extract uses.

        A column the source has not published yet comes back as all-NA rather
        than killing the load: amount_recommended did not exist before
        2026-09-09, and a snapshot from before then is still a supported input.
        """
        for name in MP_SOURCE_COLUMNS[field]:
            if name in mp.columns:
                return pd.to_numeric(mp[name], errors="coerce")
        return pd.Series(pd.NA, index=mp.index, dtype="Float64")

    out = pd.DataFrame({
        "mp_id": [safe_mp_key(n, s, h) for n, s, h in zip(mp["MP Name"], mp["State"], mp["House"])],
        "ls_term": mp["ls_term"] if "ls_term" in mp.columns else 0,
        "mp_name": mp["MP Name"],
        "constituency": mp["Constituency"],
        "state": mp["State"],
        "house": mp["House"],
        **{field: num(field) for field in MP_SOURCE_COLUMNS},
    })
    dropped = int(out["mp_id"].isna().sum())
    out = out[out["mp_id"].notna()]
    # The LS17 extract lists one MP twice - 'Manne Srinivas Reddy(17th Lok
    # Sabha)' and 'Shri Manne Srinivas Reddy (17th Lok Sabha)'. Resolving them
    # to one id is the point of mp_id, so collapse rather than fail the load.
    collapsed = int(out.duplicated(subset=["mp_id", "ls_term"]).sum())
    out = out.drop_duplicates(subset=["mp_id", "ls_term"], keep="first")
    return out, dropped, collapsed


def load_mps(conn, df):
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df[MP_COLUMNS].itertuples(index=False, name=None)
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE mps")
        execute_values(
            cur, f"INSERT INTO mps ({', '.join(MP_COLUMNS)}) VALUES %s", rows, page_size=500
        )
    conn.commit()
    return len(rows)


def prepare_insert_frame(df):
    """Add the derived columns INSERT_COLUMNS names, and select them in order.

    Built by column name rather than as a positional tuple. The positional form
    silently fell one value short when `sector` was added to INSERT_COLUMNS -
    the kind of mismatch that only surfaces against a live database, and only
    after a full load has already run.
    """
    df = df.copy()
    df["work_name"] = df["description"].str[:60]
    # A completed work's Final Amount is both what was recommended and what it
    # cost; the source records one figure (see the module docstring).
    df["recommended_amount"] = df["amount"]
    df["sanctioned_amount"] = df["amount"]
    df["source"] = "real"
    missing = [c for c in INSERT_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"INSERT_COLUMNS names columns the frame does not have: {missing}")
    return df[INSERT_COLUMNS]


def load(conn, df, rejects):
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in prepare_insert_frame(df).itertuples(index=False, name=None)
    ]
    with conn.cursor() as cur:
        # DELETE leaves every replaced row behind as a dead tuple, and the file
        # never shrinks: after a few reloads of 250k works the table was 238 MB
        # holding 114 MB of live rows, and the load eventually failed on Neon's
        # 512 MB project limit. TRUNCATE reclaims the space in the same
        # statement, so the table stays the size of its contents.
        #
        # Only when the table holds nothing but real rows, though. A database
        # carrying synthetic rows from data/generate_synthetic.py still needs
        # the targeted delete, which is what the source column is for.
        cur.execute("SELECT EXISTS (SELECT 1 FROM projects WHERE source <> 'real')")
        if cur.fetchone()[0]:
            cur.execute("DELETE FROM projects WHERE source = 'real'")
        else:
            cur.execute("TRUNCATE projects RESTART IDENTITY CASCADE")

        # Scores describe the rows that were just replaced, and they are keyed
        # on a serial the reload reassigns. Today they happened to land back on
        # the right works because the loader inserts in the same order - but a
        # single work added or removed upstream shifts every id after it, and
        # every score with it, silently and with no error. Derived data must
        # not outlive the rows it describes. scoring.py repopulates this in the
        # same pipeline run.
        cur.execute("TRUNCATE project_scores")
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
        # Every frame is built BEFORE anything is written. The works used to be
        # committed first and the MP summary parsed afterwards, so when the
        # source renamed a column on 2026-09-09 the load died on a KeyError
        # having already replaced 250,839 works - leaving one snapshot's works
        # beside the previous snapshot's payments, which is worse than either
        # snapshot alone and looks like nothing is wrong.
        df, rejects = build_rows()
        mp_df = mp_dropped = mp_collapsed = None
        if MP_SUMMARY_CSV is not None:
            mp_df, mp_dropped, mp_collapsed = build_mp_rows()
        exp_df = exp_dropped = None
        if EXPENDITURES_CSV is not None:
            exp_df, exp_dropped = build_expenditure_rows()

        inserted, rejected = load(conn, df, rejects)
        if mp_df is None:
            print("No mplads_mp_summary_*.csv in the snapshot - skipping MP aggregates.")
        else:
            print(f"Inserted {load_mps(conn, mp_df)} MP-terms "
                  f"({mp_collapsed} duplicate name(s) collapsed onto one mp_id, "
                  f"{mp_dropped} dropped for an unusable name).")
        if exp_df is None:
            print("No mplads_expenditures_*.csv in the snapshot - skipping vendor data. "
                  "Agency risk will score concentration as 0.")
        else:
            print(f"Inserted {load_expenditures(conn, exp_df)} expenditure transactions "
                  f"({exp_dropped} dropped for missing vendor, agency or amount).")
    except Exception:
        # The row stays honest as 'failed' rather than parked at 'running'
        # forever. scoring.py's own bookkeeping is unaffected since it never
        # finds this run to update.
        finish_load_run(conn, run_id, "failed", None, None)
        conn.close()
        raise

    # Still 'running': scoring.py finishes this same row once it completes.
    finish_load_run(conn, run_id, "running", inserted, rejected)
    conn.close()
    print(f"Inserted {inserted} real projects, rejected {rejected} rows.")
    print(f"Completed works' final amounts: Rs {df['expenditure'].sum():,.2f}")
