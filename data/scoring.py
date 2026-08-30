import os
from datetime import date
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, Json, execute_values
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

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


def fetch_projects(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM projects")
        return pd.DataFrame(cur.fetchall())


def compute_delay_days(row):
    if pd.isna(row["expected_completion"]):
        return 0
    end = row["actual_completion"] if pd.notna(row["actual_completion"]) else date.today()
    return max((end - row["expected_completion"]).days, 0)


def add_base_features(df):
    df["delay_days"] = df.apply(compute_delay_days, axis=1)
    df["expenditure_ratio"] = (df["expenditure"] / df["sanctioned_amount"]).round(4)

    df["district_avg_cost"] = (
        df.groupby(["district", "category"])["sanctioned_amount"].transform("mean").round(2)
    )
    df["cost_deviation_pct"] = (
        (df["sanctioned_amount"] - df["district_avg_cost"]) / df["district_avg_cost"] * 100
    ).round(2)

    df["agency_delay_rate"] = (
        df.groupby("implementing_agency")["delay_days"]
        .transform(lambda s: (s > 60).mean() * 100)
        .round(2)
    )
    return df


def add_duplicate_features(df):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    df["max_similarity_score"] = 0.0
    df["similar_work_id"] = None

    for (_district, _category), group in df.groupby(["district", "category"]):
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
                df.loc[idx, "similar_work_id"] = int(group.iloc[best_local]["id"])
    return df


def cost_risk_score(row):
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
    return float(min(row["agency_delay_rate"], 100))


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
    return min(score, 100.0), reasons


def build_flagged_reasons(row):
    reasons = list(row["compliance_reasons"])
    if row["cost_risk"] > 40:
        reasons.append(f"Cost is {row['cost_deviation_pct']:.0f}% above similar projects")
    if row["delay_risk"] > 40:
        reasons.append(f"{row['delay_days']:.0f} days beyond expected completion")
    if row["duplicate_risk"] > 40:
        reasons.append(f"{row['max_similarity_score'] * 100:.0f}% similarity with another nearby work")
    if row["agency_risk"] > 40:
        reasons.append(
            f"Implementing agency has a {row['agency_delay_rate']:.0f}% delay rate across its projects"
        )
    return reasons


def risk_level(score):
    if score < RISK_LEVEL_THRESHOLDS["LOW"]:
        return "LOW"
    if score < RISK_LEVEL_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "HIGH"


def score_dataframe(df):
    df = add_base_features(df)
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


def write_scores(conn, df):
    """Bulk-write scored columns via a temp table + single UPDATE...FROM.

    127k row-by-row UPDATEs against a remote Neon DB took hours; loading all
    rows into an unlogged TEMP TABLE with execute_values then joining in one
    UPDATE is a couple of round trips instead of 127k.
    """
    rows = [
        (
            int(row["id"]), int(row["delay_days"]), float(row["cost_deviation_pct"]),
            float(row["expenditure_ratio"]), float(row["district_avg_cost"]),
            float(row["agency_delay_rate"]), float(row["max_similarity_score"]),
            row["similar_work_id"], float(row["cost_risk"]),
            float(row["delay_risk"]), float(row["duplicate_risk"]),
            float(row["agency_risk"]), float(row["compliance_risk"]),
            float(row["overall_risk_score"]), row["risk_level"],
            Json(row["flagged_reasons"]),
        )
        for _, row in df.iterrows()
    ]
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE _score_updates (
                id INTEGER, delay_days INTEGER, cost_deviation_pct NUMERIC,
                expenditure_ratio NUMERIC, district_avg_cost NUMERIC,
                agency_delay_rate NUMERIC, max_similarity_score NUMERIC,
                similar_work_id INTEGER, cost_risk NUMERIC, delay_risk NUMERIC,
                duplicate_risk NUMERIC, agency_risk NUMERIC, compliance_risk NUMERIC,
                overall_risk_score NUMERIC, risk_level TEXT, flagged_reasons JSONB
            ) ON COMMIT DROP
            """
        )
        execute_values(
            cur,
            "INSERT INTO _score_updates VALUES %s",
            rows,
            page_size=1000,
        )
        cur.execute(
            """
            UPDATE projects SET
              delay_days = u.delay_days, cost_deviation_pct = u.cost_deviation_pct,
              expenditure_ratio = u.expenditure_ratio, district_avg_cost = u.district_avg_cost,
              agency_delay_rate = u.agency_delay_rate, max_similarity_score = u.max_similarity_score,
              similar_work_id = u.similar_work_id, cost_risk = u.cost_risk,
              delay_risk = u.delay_risk, duplicate_risk = u.duplicate_risk,
              agency_risk = u.agency_risk, compliance_risk = u.compliance_risk,
              overall_risk_score = u.overall_risk_score, risk_level = u.risk_level,
              flagged_reasons = u.flagged_reasons
            FROM _score_updates u
            WHERE projects.id = u.id
            """
        )
    conn.commit()


if __name__ == "__main__":
    # Neon drops idle connections; score_dataframe takes ~18 minutes of pure
    # CPU with no DB activity, so a connection held open across it is dead by
    # the time we get to write_scores. Fetch on one connection, close it,
    # compute, then open a fresh connection to write.
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    df = fetch_projects(conn)
    conn.close()

    # Controller-approved deviation: RealDictCursor returns NUMERIC columns as
    # decimal.Decimal, which makes these columns object-dtype and breaks
    # pandas arithmetic (/, .round(), groupby().transform("mean")) used below.
    # Cast to float right after loading; unit tests build their own Series
    # and are unaffected.
    for col in ("sanctioned_amount", "expenditure", "recommended_amount"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    scored = score_dataframe(df)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    write_scores(conn, scored)
    conn.close()
    print(f"Scored {len(scored)} projects.")
