import os
from datetime import date
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

RISK_WEIGHTS = {"cost": 0.25, "delay": 0.25, "duplicate": 0.20, "agency": 0.15, "compliance": 0.15}
RISK_LEVEL_THRESHOLDS = {"LOW": 40, "MEDIUM": 70}
DUPLICATE_SIMILARITY_THRESHOLD = 0.85


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
    if row["max_similarity_score"] >= DUPLICATE_SIMILARITY_THRESHOLD:
        return float(min(row["max_similarity_score"] * 100, 100))
    return 0.0


def agency_risk_score(row):
    return float(min(row["agency_delay_rate"], 100))


def compliance_risk_score(row):
    score, reasons = 0.0, []
    if row["expenditure"] > row["sanctioned_amount"]:
        score += 60
        reasons.append("Expenditure exceeds sanctioned amount")
    if pd.isna(row["start_date"]) or pd.isna(row["expected_completion"]):
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
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """
                UPDATE projects SET
                  delay_days=%s, cost_deviation_pct=%s, expenditure_ratio=%s,
                  district_avg_cost=%s, agency_delay_rate=%s,
                  max_similarity_score=%s, similar_work_id=%s,
                  cost_risk=%s, delay_risk=%s, duplicate_risk=%s,
                  agency_risk=%s, compliance_risk=%s,
                  overall_risk_score=%s, risk_level=%s, flagged_reasons=%s
                WHERE id=%s
                """,
                (
                    int(row["delay_days"]), float(row["cost_deviation_pct"]),
                    float(row["expenditure_ratio"]), float(row["district_avg_cost"]),
                    float(row["agency_delay_rate"]), float(row["max_similarity_score"]),
                    row["similar_work_id"], float(row["cost_risk"]),
                    float(row["delay_risk"]), float(row["duplicate_risk"]),
                    float(row["agency_risk"]), float(row["compliance_risk"]),
                    float(row["overall_risk_score"]), row["risk_level"],
                    Json(row["flagged_reasons"]), int(row["id"]),
                ),
            )
    conn.commit()


if __name__ == "__main__":
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    df = fetch_projects(conn)
    # Controller-approved deviation: RealDictCursor returns NUMERIC columns as
    # decimal.Decimal, which makes these columns object-dtype and breaks
    # pandas arithmetic (/, .round(), groupby().transform("mean")) used below.
    # Cast to float right after loading; unit tests build their own Series
    # and are unaffected.
    for col in ("sanctioned_amount", "expenditure", "recommended_amount"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    scored = score_dataframe(df)
    write_scores(conn, scored)
    print(f"Scored {len(scored)} projects.")
    conn.close()
