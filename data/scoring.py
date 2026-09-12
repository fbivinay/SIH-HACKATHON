import os
import sys
from datetime import date
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, Json, execute_values
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

import detectors
import llm_sectors
import vendors
from sectors import classify_sector
from sectors import normalize as sectors_normalize
from sectors import verify as sectors_verify

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

RISK_WEIGHTS = {"cost": 0.25, "delay": 0.25, "duplicate": 0.20, "agency": 0.15, "compliance": 0.15}
RISK_LEVEL_THRESHOLDS = {"LOW": 40, "MEDIUM": 70}
# Calibrated against the observed max_similarity_score distribution (see
# task-3-report.md). Descriptions are only ever compared within the same
# (district, category) group, so every pair is already about the same kind of
# work in the same place and all-MiniLM-L6-v2 cosine similarity has a ~0.90
# median baseline there — 0.85 sat in the noise and fired on 1212/1500 rows.
# 0.94 (~p82) is the foot of the genuine near-duplicate tail; combined with the
# rescaling in duplicate_risk_score it puts the "> 40" reporting line at
# similarity ~0.964 (~p97.5), which fires on 52/1500 rows.
DUPLICATE_SIMILARITY_THRESHOLD = 0.94

# A cost baseline needs enough peers to be a baseline. Below this, a work scores
# no cost risk at all rather than being compared against a median of three. The
# floor matters most in the long tail: 40% of (district, sector) groups hold
# fewer than 8 works, and before this guard every one of them produced a
# confident-looking deviation from noise.
MIN_PEERS = 8


def fetch_projects(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # The base table, not the view: this is the input scoring is about to
        # replace, and reading its own previous output would be circular.
        #
        # work_key IS NOT NULL because project_scores is keyed on it, so a row
        # without one cannot be scored at all. It used to be keyed on
        # projects.id, which is never null, so nothing needed saying. The rows
        # this excludes are the synthetic demo rows generate_synthetic.py
        # writes without a work_key - which load() deliberately preserves -
        # and scoring them would abort the whole pass on a not-null violation
        # after ~50 minutes of computation, at the very last statement.
        cur.execute("SELECT COUNT(*) FROM projects WHERE work_key IS NULL")
        unkeyed = cur.fetchone()["count"]
        if unkeyed:
            print(f"Skipping {unkeyed:,} project(s) with no work_key - they cannot "
                  "be scored, because a score is keyed on work_key.")
        cur.execute("SELECT * FROM projects WHERE work_key IS NOT NULL")
        return pd.DataFrame(cur.fetchall())


def fetch_expenditures(conn):
    """Raw expenditure transactions, or an empty frame if none were loaded.

    A snapshot without an expenditure file is a supported case (the 2026-08-30
    one had none), so this must not be the thing that fails a scoring run.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT implementing_agency, ls_term, vendor, expenditure_amount, "
            "expenditure_date, payment_status FROM expenditures"
        )
        df = pd.DataFrame(cur.fetchall())
    if not df.empty:
        df["expenditure_amount"] = df["expenditure_amount"].astype(float)
    return df


def fetch_mps(conn):
    """MP-term aggregates, or an empty frame if the snapshot carried no MP
    summary file - the same supported case as fetch_expenditures."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT mp_id, ls_term, mp_name, constituency, state, allocated_amount, "
            "amount_recommended, unspent_amount, utilization_pct, completed_works, "
            "recommended_works FROM mps"
        )
        df = pd.DataFrame(cur.fetchall())
    for col in ("allocated_amount", "amount_recommended", "unspent_amount", "utilization_pct"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    return df


def write_detector_findings(conn, findings):
    """Replace the whole findings set. They are derived, cheap to recompute and
    meaningless once the data under them has moved, so there is no history to
    preserve - the same contract as agency_vendor_profile."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE detector_findings RESTART IDENTITY")
        if findings:
            execute_values(
                cur,
                "INSERT INTO detector_findings "
                "(code, subject_type, subject, ls_term, period, severity, headline, evidence) "
                "VALUES %s",
                [
                    (f["code"], f["subject_type"], f["subject"], f["ls_term"],
                     f["period"], f["severity"], f["headline"], Json(f["evidence"]))
                    for f in findings
                ],
                page_size=1000,
            )
    conn.commit()
    return len(findings)


def write_agency_vendor_profile(conn, profile):
    columns = vendors.PROFILE_COLUMNS
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in profile[columns].itertuples(index=False, name=None)
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE agency_vendor_profile")
        if rows:
            execute_values(
                cur,
                f"INSERT INTO agency_vendor_profile ({', '.join(columns)}) VALUES %s",
                rows,
                page_size=500,
            )
    conn.commit()


def compute_delay_days(row):
    if pd.isna(row["expected_completion"]):
        return 0
    end = row["actual_completion"] if pd.notna(row["actual_completion"]) else date.today()
    return max((end - row["expected_completion"]).days, 0)


def add_base_features(df):
    df["delay_days"] = df.apply(compute_delay_days, axis=1)
    df["expenditure_ratio"] = (df["expenditure"] / df["sanctioned_amount"]).round(4)

    # Peers are (district, sector), not (district, category). `category` is
    # 'Normal/Others' for 98.1% of rows, so the old key compared a street light
    # against a district average containing roads. sector comes from the
    # description via sectors.py; recompute it here if the rows predate the
    # column, so scoring a stale database degrades to correct-but-slower rather
    # than silently grouping every work in a district together.
    if "sector" not in df.columns or df["sector"].isna().any():
        df["sector"] = df["description"].map(classify_sector)
        # Raises if the keyword rules stop matching this data. The cost
        # baseline needs a stratifier that carries information; without this
        # a source that changes its description style would quietly send every
        # work into one bucket and compare it against every other work.
        # It lives here because this is where sector is derived - `projects`
        # holds only what the source publishes.
        sectors_verify(df["description"])

    # Anything the keyword rules left in Other gets whatever label the model
    # assigned on a previous run of scripts/classify_sectors.py. Reading a cache
    # rather than calling anything keeps scoring offline, deterministic and free
    # - the network call is a separate, deliberate step.
    unresolved = df["sector"] == llm_sectors.OTHER
    if unresolved.any():
        cache = llm_sectors.load_cache()
        if cache:
            labelled = df.loc[unresolved, "description"].map(
                lambda d: cache.get(sectors_normalize(d), llm_sectors.OTHER)
            )
            moved = int((labelled != llm_sectors.OTHER).sum())
            df.loc[unresolved, "sector"] = labelled
            print(f"sectors: {moved:,} works moved out of Other by the cached "
                  f"model labels ({len(cache):,} descriptions in the cache).")

    peers = df.groupby(["district", "sector"])["sanctioned_amount"]
    # Median, not mean: a single Rs 7.5 crore work drags a district mean far
    # enough that the works either side of it both look normal.
    df["peer_median_cost"] = peers.transform("median").round(2)
    df["peer_count"] = peers.transform("size")
    df["cost_deviation_pct"] = (
        (df["sanctioned_amount"] - df["peer_median_cost"]) / df["peer_median_cost"] * 100
    ).round(2)
    # Too few peers to compare against: no claim, rather than a confident one.
    df.loc[df["peer_count"] < MIN_PEERS, "cost_deviation_pct"] = 0.0

    df["agency_delay_rate"] = (
        df.groupby("implementing_agency")["delay_days"]
        .transform(lambda s: (s > 60).mean() * 100)
        .round(2)
    )
    return df


def add_duplicate_features(df):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    df["max_similarity_score"] = 0.0
    df["similar_work_key"] = None

    for (_district, _sector), group in df.groupby(["district", "sector"]):
        if len(group) < 2:
            continue
        embeddings = model.encode(group["description"].fillna("").tolist())
        sims = cosine_similarity(embeddings)
        for local_i, idx in enumerate(group.index):
            row_sims = sims[local_i].copy()
            row_sims[local_i] = -1
            best_local = row_sims.argmax()
            best_score = row_sims[best_local]
            if best_score > df.loc[idx, "max_similarity_score"]:
                df.loc[idx, "max_similarity_score"] = round(float(best_score), 4)
                df.loc[idx, "similar_work_key"] = group.iloc[best_local]["work_key"]
    return df


def cost_risk_score(row):
    """Cost risk from deviation above the peer median, 0 when peers are thin.

    add_base_features already zeroes cost_deviation_pct below MIN_PEERS; the
    guard is repeated here so the function is correct when called directly, as
    the tests do.
    """
    if row.get("peer_count") is not None and row["peer_count"] < MIN_PEERS:
        return 0.0
    dev = row["cost_deviation_pct"]
    return float(min(max(dev, 0), 100)) if dev > 0 else 0.0


def delay_risk_score(row):
    return float(min(row["delay_days"] / 180 * 100, 100))


def duplicate_risk_score(row):
    """Map similarity [THRESHOLD, 1.0] onto risk [0, 100].

    Returning raw similarity * 100 made a barely-over-threshold match score ~94,
    indistinguishable from a verbatim copy. Rescaling means crossing the line by
    a hair scores near 0 and only a near-identical description scores near 100.
    """
    sim = row["max_similarity_score"]
    if sim < DUPLICATE_SIMILARITY_THRESHOLD:
        return 0.0
    scaled = (sim - DUPLICATE_SIMILARITY_THRESHOLD) / (1.0 - DUPLICATE_SIMILARITY_THRESHOLD) * 100
    return float(min(max(scaled, 0.0), 100.0))


def agency_risk_score(row):
    """Worst of the agency's signals, not a weighted blend.

    Blending would dilute: an agency with a 70% delay rate would drop to 35
    the moment a second component was added at half weight, silently lowering
    every score in the system in a change that was supposed to be additive.
    Taking the max keeps the existing delay behaviour intact and lets a newly
    measured signal only ever raise a score - the same choice score_dataframe
    already makes when folding the Isolation Forest into cost_risk.

    It also stays explainable: exactly one component is responsible for the
    number, and build_flagged_reasons names it.
    """
    return round(max(
        float(min(row.get("agency_delay_rate") or 0.0, 100.0)),
        float(row.get("agency_concentration_risk") or 0.0),
        vendors.pending_risk(row.get("agency_oldest_pending_days")),
    ), 2)


def compliance_risk_score(row):
    score, reasons = 0.0, []
    if row["expenditure"] > row["sanctioned_amount"]:
        score += 60
        reasons.append("Expenditure exceeds sanctioned amount")
    # Only recommended works are guaranteed a recommendation date in the source
    # data (see load_real_data.py); most completed works simply have none on
    # record, so this rule would misreport a data gap as an agency compliance
    # failure if applied to them. Scope it to rows where the date should be
    # knowable.
    if row["work_status"] == "recommended" and (
        pd.isna(row["start_date"]) or pd.isna(row["expected_completion"])
    ):
        score += 20
        reasons.append("Missing start or expected completion date")
    if row["work_status"] == "completed" and pd.isna(row["actual_completion"]):
        score += 20
        reasons.append("Marked completed with no actual completion date")
    # has_images can arrive as object dtype (True/False/None) once it's round-
    # tripped through psycopg2 + pandas, so NaN/None must not read as truthy
    # False. Require it to be exactly False - pd.notna guards NaN/None first,
    # then compare, rather than relying on `not row["has_images"]` which would
    # treat NULL (unknown) the same as a recorded absence of images. row.get
    # keeps this safe against hand-built test Series that omit the column.
    has_images = row.get("has_images")
    if row["work_status"] == "completed" and pd.notna(has_images) and has_images == False:  # noqa: E712
        score += 30
        reasons.append("Completed work has no photographic documentation on record")
    return min(score, 100.0), reasons


def build_flagged_reasons(row):
    reasons = list(row["compliance_reasons"])
    # Gate the cost sentence on the cost deviation itself, NOT on cost_risk.
    # cost_risk is deliberately blended with the Isolation Forest score (see
    # score_dataframe), which is fit on sanctioned_amount + delay_days +
    # expenditure_ratio — so a work that is only a delay/spend outlier can push
    # cost_risk over 40 while its actual cost deviation is negative. Gating the
    # text on cost_risk produced "Cost is -56% above similar projects" on 3,539
    # real works. A flagged reason that contradicts itself is worse than no
    # reason at all when the whole premise is explainable alerts.
    # State the comparison basis. "40% above similar projects" is unactionable
    # if the verifier cannot see which projects, how many, or what the median
    # was - and the peer guard means a reason is only ever emitted where that
    # basis exists.
    peer_count = row.get("peer_count")
    peer_median = row.get("peer_median_cost")
    amount = row.get("sanctioned_amount")
    # No basis, no claim. In a scored run add_base_features always supplies all
    # three, so this only bites on rows that predate the columns - where saying
    # nothing beats quoting a comparison we cannot show.
    has_basis = (
        peer_median is not None and not pd.isna(peer_median)
        and amount is not None and not pd.isna(amount)
        and (peer_count is None or pd.isna(peer_count) or peer_count >= MIN_PEERS)
    )
    if row["cost_deviation_pct"] > 40 and has_basis:
        peers = "" if peer_count is None or pd.isna(peer_count) else f", {int(peer_count)} peer works"
        reasons.append(
            f"\u20b9{float(amount):,.0f} against a \u20b9{float(peer_median):,.0f} median "
            f"for {row.get('sector') or 'similar'} works in {row['district']} "
            f"({row['cost_deviation_pct']:.0f}% above{peers})"
        )
    elif row.get("iso_anomaly", 0) > 40:
        # The multivariate signal is real and is driving this work's score, so
        # narrate it honestly rather than silently dropping the explanation.
        # Name the model. This is the one flag a reviewer cannot reproduce by
        # eye - no single column is out of range, which is exactly the point -
        # so the reason has to say what found it.
        reasons.append(
            "Unusual combination of sanctioned amount, delay and spending "
            "pattern — flagged by an isolation forest fitted over every work, "
            "not by any single figure being out of range"
        )
    if row["delay_risk"] > 40:
        reasons.append(f"{row['delay_days']:.0f} days beyond expected completion")
    if row["duplicate_risk"] > 40:
        reasons.append(f"{row['max_similarity_score'] * 100:.0f}% similarity with another nearby work")
    if row["agency_risk"] > 40:
        # Name the component actually responsible. agency_risk is a max, so
        # attributing it to the delay rate unconditionally would have reported
        # a delay problem on an agency flagged purely for vendor concentration.
        delay = float(min(row.get("agency_delay_rate") or 0.0, 100.0))
        concentration = float(row.get("agency_concentration_risk") or 0.0)
        pending = vendors.pending_risk(row.get("agency_oldest_pending_days"))
        driver = max(delay, concentration, pending)
        if driver == delay:
            reasons.append(
                f"Implementing agency has a {delay:.0f}% delay rate across its projects"
            )
        elif driver == concentration:
            reasons.append(vendors.concentration_reason({
                "concentration_risk": concentration,
                "top_vendor_share_pct": row.get("agency_top_vendor_share_pct"),
                "total_spend": row.get("agency_total_spend"),
                "top_vendor": row.get("agency_top_vendor"),
                "vendor_count": row.get("agency_vendor_count"),
                "transaction_count": row.get("agency_transaction_count"),
            }))
        else:
            reasons.append(vendors.pending_reason({
                "oldest_pending_days": row.get("agency_oldest_pending_days"),
                "pending_count": row.get("agency_pending_count"),
            }))
    return [r for r in reasons if r]


def risk_level(score):
    if score < RISK_LEVEL_THRESHOLDS["LOW"]:
        return "LOW"
    if score < RISK_LEVEL_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "HIGH"


AGENCY_PROFILE_COLUMNS = [
    "concentration_risk", "oldest_pending_days", "pending_count", "top_vendor",
    "top_vendor_share_pct", "total_spend", "vendor_count", "transaction_count",
]


def attach_agency_profile(df, profile):
    """Left-join the per-agency-per-term vendor profile onto works.

    Keyed on (implementing_agency, ls_term): an agency's vendor mix in one Lok
    Sabha term says nothing about its mix in the other, so a work must be
    matched against its own term's profile.

    Left, not inner: an agency with no expenditure rows keeps its works and
    scores concentration 0, rather than dropping them out of the dataset.
    """
    for col in AGENCY_PROFILE_COLUMNS:
        df[f"agency_{col}"] = None
    if profile is None or profile.empty:
        return df

    term = (df["ls_term"] if "ls_term" in df.columns else pd.Series(0, index=df.index))
    key = pd.Series(
        list(zip(df["implementing_agency"], term.fillna(0).astype(int))), index=df.index
    )
    indexed = profile.set_index(
        pd.MultiIndex.from_arrays([profile["implementing_agency"], profile["ls_term"].astype(int)])
    )
    for col in AGENCY_PROFILE_COLUMNS:
        if col in indexed.columns:
            df[f"agency_{col}"] = key.map(indexed[col])
    return df


def score_dataframe(df, agency_profile=None):
    df = add_base_features(df)
    df = attach_agency_profile(df, agency_profile)
    df = add_duplicate_features(df)

    df["cost_risk"] = df.apply(cost_risk_score, axis=1)
    df["delay_risk"] = df.apply(delay_risk_score, axis=1)
    df["duplicate_risk"] = df.apply(duplicate_risk_score, axis=1)
    df["agency_risk"] = df.apply(agency_risk_score, axis=1)

    compliance = df.apply(compliance_risk_score, axis=1)
    df["compliance_risk"] = compliance.apply(lambda t: t[0])
    df["compliance_reasons"] = compliance.apply(lambda t: t[1])

    iso_features = df[["sanctioned_amount", "delay_days", "expenditure_ratio"]].fillna(0)
    iso = IsolationForest(random_state=42, contamination=0.05)
    iso.fit(iso_features)
    anomaly_score = iso.decision_function(iso_features) * -1
    normalized = (
        (anomaly_score - anomaly_score.min())
        / (anomaly_score.max() - anomaly_score.min() + 1e-9)
        * 100
    )
    # Keep the blend for scoring (the IF genuinely detects outliers the cost
    # rule misses), but retain the raw IF score so build_flagged_reasons can
    # tell "expensive vs peers" apart from "statistically odd overall" and
    # narrate each accurately. Not persisted — write_scores names its columns.
    df["iso_anomaly"] = normalized
    df["cost_risk"] = df[["cost_risk"]].assign(iso=normalized).max(axis=1)

    df["overall_risk_score"] = (
        df["cost_risk"] * RISK_WEIGHTS["cost"]
        + df["delay_risk"] * RISK_WEIGHTS["delay"]
        + df["duplicate_risk"] * RISK_WEIGHTS["duplicate"]
        + df["agency_risk"] * RISK_WEIGHTS["agency"]
        + df["compliance_risk"] * RISK_WEIGHTS["compliance"]
    ).round(2)
    df["risk_level"] = df["overall_risk_score"].apply(risk_level)
    df["flagged_reasons"] = df.apply(build_flagged_reasons, axis=1)
    return df


# A load and the scoring that follows it run minutes apart in the same job. A
# 'running' row older than this belongs to some earlier, abandoned attempt, and
# adopting it would stamp that attempt as this run's success.
MAX_RUN_ADOPTION_AGE = "12 hours"


def load_was_skipped(conn):
    """True when the most recent load finished 'success' with the unchanged
    note and no scoring has happened since - i.e. load_real_data.py found
    tonight's extract identical to the last one and rewrote nothing. There is
    then nothing for this pass to do either: the scores in the table were
    computed from exactly these rows. Rewriting them would cost 113 MB of
    transient space on a database that has ~157 MB to spare."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT notes FROM data_refresh
                   WHERE finished_at > now() - INTERVAL '2 hours'
                   ORDER BY id DESC LIMIT 1"""
            )
            row = cur.fetchone()
        return bool(row and row[0] and row[0].startswith("unchanged:"))
    except Exception as e:  # noqa: BLE001
        print(f"data_refresh: could not check for a skipped load: {e}")
        conn.rollback()
        return False


def current_refresh_run_id(conn):
    """Find the 'running' data_refresh row load_real_data.py started, so this
    run's rows_scored/status lands on the same audit row. Best-effort: audit
    bookkeeping must never block scoring itself.

    load_real_data.py already closes abandoned rows when it starts, so in the
    normal pipeline there is exactly one candidate. The age bound covers running
    scoring.py on its own against a database whose last load was killed."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM data_refresh WHERE status = 'running' "
                f"AND started_at > now() - INTERVAL '{MAX_RUN_ADOPTION_AGE}' "
                "ORDER BY started_at DESC LIMIT 1"
            )
            row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:  # noqa: BLE001
        print(f"data_refresh: failed to look up running run: {e}")
        return None


def finish_scoring_run(conn, run_id, status, rows_scored):
    if run_id is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE data_refresh
                   SET finished_at = now(), status = %s, rows_scored = %s
                   WHERE id = %s""",
                [status, rows_scored, run_id],
            )
        conn.commit()
    except Exception as e:  # noqa: BLE001
        print(f"data_refresh: failed to update run {run_id}: {e}")
        conn.rollback()


SCORE_COLUMNS = [
    "work_key", "delay_days", "cost_deviation_pct", "expenditure_ratio", "sector",
    "peer_median_cost", "peer_count", "agency_delay_rate", "max_similarity_score",
    "similar_work_key", "cost_risk", "delay_risk", "duplicate_risk", "agency_risk",
    "compliance_risk", "overall_risk_score", "risk_level", "flagged_reasons",
]


def write_scores(conn, df):
    """Replace project_scores wholesale.

    This used to UPDATE every row of `projects`. Postgres writes a new version
    of each row an UPDATE touches, so a run doubled a 161 MB table and took the
    database from 300 MB to 457 MB against Neon's 512 MB limit - reclaimable
    only by a VACUUM FULL, which needs room for a whole copy of the table at
    exactly the moment there is none.

    TRUNCATE reclaims in the same statement, so this table stays the size of
    its contents and `projects` is never rewritten after the load. Reads go
    through the projects_scored view, which joins the two back together.

    The TRUNCATE and the INSERT share one transaction, so a reader either sees
    the whole previous run or the whole new one, never an empty table. That is
    what lets the loader leave this table alone: rows keyed on work_key stay
    correctly attached to their works until the moment they are replaced.
    """
    rows = [
        (
            row["work_key"], int(row["delay_days"]), float(row["cost_deviation_pct"]),
            float(row["expenditure_ratio"]), row["sector"],
            float(row["peer_median_cost"]), int(row["peer_count"]),
            float(row["agency_delay_rate"]), float(row["max_similarity_score"]),
            row["similar_work_key"], float(row["cost_risk"]),
            float(row["delay_risk"]), float(row["duplicate_risk"]),
            float(row["agency_risk"]), float(row["compliance_risk"]),
            float(row["overall_risk_score"]), row["risk_level"],
            Json(row["flagged_reasons"]),
        )
        for _, row in df.iterrows()
    ]
    # TRUNCATE holds the old file until COMMIT (measured - see
    # load_real_data.check_headroom), so this rewrite needs headroom equal to
    # the table's own size. Refuse with the arithmetic rather than die on
    # DiskFull two thirds of the way through the INSERT.
    with conn.cursor() as cur:
        cur.execute("SELECT pg_database_size(current_database()), "
                    "pg_total_relation_size('project_scores')")
        at_rest, table = cur.fetchone()
    conn.rollback()
    limit = 512 * 1024 * 1024
    mb = lambda b: f"{b / 1048576:.0f} MB"
    print(f"headroom: database {mb(at_rest)} at rest, project_scores {mb(table)}, "
          f"peak {mb(at_rest + table)} against {mb(limit)}")
    if at_rest + table > limit * 0.97:
        raise SystemExit(f"refusing to write scores: rewrite would peak at "
                         f"{mb(at_rest + table)} against {mb(limit)}. Nothing written; "
                         f"the previous run's scores are intact.")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE project_scores")
        execute_values(
            cur,
            f"INSERT INTO project_scores ({', '.join(SCORE_COLUMNS)}) VALUES %s",
            rows,
            page_size=1000,
        )
    conn.commit()


if __name__ == "__main__":
    # Neon drops idle connections; score_dataframe takes ~18 minutes of pure
    # CPU with no DB activity, so a connection held open across it is dead by
    # the time we get to write_scores. Fetch on one connection, close it,
    # compute, then open a fresh connection to write.
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    if os.environ.get("SCORE_FORCE") != "1" and load_was_skipped(conn):
        conn.close()
        print("Load reported the extract unchanged; the scores in project_scores "
              "were computed from these exact rows. Nothing to do. "
              "(SCORE_FORCE=1 to re-score anyway, e.g. after changing scoring.py.)")
        sys.exit(0)
    run_id = current_refresh_run_id(conn)
    df = fetch_projects(conn)
    expenditures = fetch_expenditures(conn)
    mp_rows = fetch_mps(conn)
    conn.close()

    agency_profile = vendors.build_agency_vendor_profile(expenditures, as_of=date.today())
    if agency_profile.empty:
        print("No expenditure rows loaded - agency concentration scores 0 for every agency.")
    else:
        print(f"Profiled {len(agency_profile)} agencies over "
              f"{len(expenditures):,} expenditure transactions.")

    # Controller-approved deviation: RealDictCursor returns NUMERIC columns as
    # decimal.Decimal, which makes these columns object-dtype and breaks
    # pandas arithmetic (/, .round(), groupby().transform("mean")) used below.
    # Cast to float right after loading; unit tests build their own Series
    # and are unaffected.
    for col in ("sanctioned_amount", "expenditure", "recommended_amount"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    try:
        scored = score_dataframe(df, agency_profile=agency_profile)
    except Exception:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        finish_scoring_run(conn, run_id, "failed", None)
        conn.close()
        raise

    # Cohort detectors run on the same frames but never touch a work's score -
    # see data/detectors.py for why a population statistic stays at population
    # grain.
    #
    # The scores are written FIRST. This comment used to claim a detector
    # failure could not lose a completed scoring pass, and it was wrong: the
    # detectors ran before the write, outside the try/except above, so any
    # exception from run_all discarded fifty minutes of finished work that was
    # sitting in memory. That was not theoretical - run_all raised KeyError on
    # the empty frames fetch_expenditures documents as supported.
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    write_agency_vendor_profile(conn, agency_profile)
    write_scores(conn, scored)
    finish_scoring_run(conn, run_id, "success", len(scored))
    print(f"Scored {len(scored)} projects.")

    # Now the detectors, with the scores already safe. A failure here costs the
    # findings and says so; it no longer costs the pass.
    findings, written = [], 0
    try:
        findings = detectors.run_all(df, expenditures, mp_rows)
        written = write_detector_findings(conn, findings)
    except Exception as err:  # noqa: BLE001 - the scores are already committed
        print(f"Detectors failed after the scores were written: "
              f"{type(err).__name__}: {err}")
    conn.close()
    by_code = {}
    for f in findings:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    print(f"Wrote {written} detector findings: "
          + ", ".join(f"{c} x{n}" for c, n in sorted(by_code.items())))
