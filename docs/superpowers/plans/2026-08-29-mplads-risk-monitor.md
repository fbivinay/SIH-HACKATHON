# MPLADS Risk Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a demo-ready MPLADS project risk monitor: batch-scored risk data in Postgres, a read-only FastAPI backend, and a 4-screen Next.js dashboard, deployed and ready for a live SIH demo.

**Architecture:** All ML/rule scoring runs once, offline, in a Python batch script that writes final risk scores into Postgres. FastAPI only reads already-scored rows — nothing user-facing triggers live inference. Next.js consumes the API. Three independent tracks (data, api, web) share one contract: the Postgres schema (Task 0) and the API response shapes (Task 4).

**Tech Stack:** Python (pandas, scikit-learn, sentence-transformers, psycopg2), PostgreSQL, FastAPI, Next.js + Tailwind CSS, Leaflet, Vercel.

**Spec:** `docs/superpowers/specs/2026-08-29-mplads-risk-monitor-design.md`

## Global Constraints

- Risk weights: cost 25%, delay 25%, duplicate 20%, agency 15%, compliance 15% (`RISK_WEIGHTS` in `data/scoring.py`).
- Risk level bands: LOW `< 40`, MEDIUM `40–70`, HIGH `> 70`.
- Duplicate similarity threshold: `0.85` (`sentence-transformers`, model `all-MiniLM-L6-v2`).
- Explanations are template-generated from `flagged_reasons`, filled with real computed numbers. No live LLM call anywhere in the critical path.
- No Kafka, no auth/login, no district-level interactive map (state-level choropleth + district table instead), no AWS — Vercel only.
- All scoring is a one-time offline batch job (Task 3). The API and frontend never trigger scoring.
- Table/column names, exactly as used throughout every task below: `projects` table per Task 0's `schema.sql`. Do not rename.

---

## Task 0: Postgres schema + repo scaffold + shared env contract

**Files:**
- Create: `data/schema.sql`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Produces: the `projects` table (all columns below) and `rejected_rows` table, which every later task reads/writes by these exact names. Produces `DATABASE_URL` as the one shared env var name every track uses.

- [ ] **Step 1: Provision a managed Postgres database**

Invoke the `vercel:marketplace` skill and follow it to provision a Postgres database (Neon, via the Vercel Marketplace, is the current Vercel-native default — the skill will confirm or route you to an alternative). You need a `DATABASE_URL` connection string reachable both from your local machine (for the batch script) and from Vercel (for the deployed API).

- [ ] **Step 2: Write the schema**

```sql
-- data/schema.sql
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    work_name TEXT NOT NULL,
    description TEXT,
    mp_name TEXT,
    constituency TEXT,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    category TEXT NOT NULL,
    implementing_agency TEXT NOT NULL,
    recommended_amount NUMERIC(14,2),
    sanctioned_amount NUMERIC(14,2) NOT NULL,
    expenditure NUMERIC(14,2) NOT NULL DEFAULT 0,
    work_status TEXT NOT NULL,
    start_date DATE,
    expected_completion DATE,
    actual_completion DATE,
    source TEXT NOT NULL DEFAULT 'synthetic',

    delay_days INTEGER,
    cost_deviation_pct NUMERIC(6,2),
    expenditure_ratio NUMERIC(6,2),
    district_avg_cost NUMERIC(14,2),
    agency_delay_rate NUMERIC(5,2),
    max_similarity_score NUMERIC(5,4),
    similar_work_id INTEGER REFERENCES projects(id),

    cost_risk NUMERIC(5,2),
    delay_risk NUMERIC(5,2),
    duplicate_risk NUMERIC(5,2),
    agency_risk NUMERIC(5,2),
    compliance_risk NUMERIC(5,2),
    overall_risk_score NUMERIC(5,2),
    risk_level TEXT,
    flagged_reasons JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rejected_rows (
    id SERIAL PRIMARY KEY,
    raw_row JSONB NOT NULL,
    reason TEXT NOT NULL,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);
CREATE INDEX IF NOT EXISTS idx_projects_district ON projects(district);
CREATE INDEX IF NOT EXISTS idx_projects_agency ON projects(implementing_agency);
CREATE INDEX IF NOT EXISTS idx_projects_risk_level ON projects(risk_level);
```

- [ ] **Step 3: Apply the schema**

Run: `psql "$DATABASE_URL" -f data/schema.sql`
Expected: `CREATE TABLE` x2, `CREATE INDEX` x4, no errors.

- [ ] **Step 4: Write shared env template and gitignore**

```bash
# .env.example
DATABASE_URL=postgres://user:password@host:5432/dbname
```

```gitignore
# .gitignore
.env
__pycache__/
*.pyc
node_modules/
web/.next/
.vercel/
```

Copy `.env.example` to `.env` in the repo root and fill in the real `DATABASE_URL` from Step 1. Every Python script in `data/` and `api/` loads this same root `.env` (see Task 1 Step 1 for the exact loading pattern — do not duplicate `.env` files per subfolder).

- [ ] **Step 5: Commit**

```bash
git add data/schema.sql .env.example .gitignore README.md
git commit -m "chore: add Postgres schema and repo scaffold"
git push
```

---

## Task 1: Synthetic data generator (Track: data)

**Files:**
- Create: `data/requirements.txt`
- Create: `data/generate_synthetic.py`

**Interfaces:**
- Consumes: `DATABASE_URL` from root `.env` (Task 0).
- Produces: ~1500 rows in `projects` with `source='synthetic'`, including deliberately seeded cost, delay, agency, and duplicate anomalies for the scoring engine (Task 3) to catch.

- [ ] **Step 1: Write requirements**

```
# data/requirements.txt
pandas
scikit-learn
sentence-transformers
psycopg2-binary
python-dotenv
Faker
```

Run: `python -m venv data/.venv && source data/.venv/bin/activate && pip install -r data/requirements.txt`

- [ ] **Step 2: Write the generator**

```python
# data/generate_synthetic.py
import os
import random
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from faker import Faker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
fake = Faker("en_IN")
random.seed(42)

STATES_DISTRICTS = {
    "Maharashtra": ["Pune", "Nagpur", "Nashik"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi"],
    "Tamil Nadu": ["Chennai", "Madurai", "Coimbatore"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Belagavi"],
    "West Bengal": ["Kolkata", "Howrah", "Darjeeling"],
}
CATEGORIES = ["Drinking Water", "Road Construction", "School Infrastructure",
              "Community Hall", "Street Lighting", "Health Facility"]
AGENCIES = [f"Agency {c}" for c in "ABCDEFGH"]
WORK_TEMPLATES = {
    "Drinking Water": "Installation of drinking water supply system in {place}",
    "Road Construction": "Construction/repair of road connecting {place}",
    "School Infrastructure": "Construction of additional classroom at {place} school",
    "Community Hall": "Construction of community hall at {place}",
    "Street Lighting": "Installation of solar street lights in {place}",
    "Health Facility": "Upgradation of primary health centre at {place}",
}
BASE_COST = {
    "Drinking Water": 800000, "Road Construction": 1500000,
    "School Infrastructure": 600000, "Community Hall": 900000,
    "Street Lighting": 300000, "Health Facility": 1200000,
}


def make_project(force_anomaly=None):
    state = random.choice(list(STATES_DISTRICTS))
    district = random.choice(STATES_DISTRICTS[state])
    category = random.choice(CATEGORIES)
    place = f"{fake.city_suffix()} {district}"
    base = BASE_COST[category]
    agency = random.choice(AGENCIES)

    sanctioned = base * random.uniform(0.85, 1.15)
    start = date(2022, 1, 1) + timedelta(days=random.randint(0, 700))
    expected_completion = start + timedelta(days=random.randint(90, 365))
    actual_delay = random.randint(-10, 30)
    expenditure = sanctioned * random.uniform(0.7, 1.0)

    if force_anomaly == "cost":
        sanctioned = base * random.uniform(2.2, 3.0)
    elif force_anomaly == "delay":
        actual_delay = random.randint(120, 400)
    elif force_anomaly == "agency":
        agency = "Agency X"
        actual_delay = random.randint(150, 300)

    actual_completion = expected_completion + timedelta(days=actual_delay)
    description = WORK_TEMPLATES[category].format(place=place)

    return {
        "work_name": description[:60],
        "description": description,
        "mp_name": fake.name(),
        "constituency": f"{district} constituency",
        "state": state,
        "district": district,
        "category": category,
        "implementing_agency": agency,
        "recommended_amount": round(sanctioned, 2),
        "sanctioned_amount": round(sanctioned, 2),
        "expenditure": round(expenditure, 2),
        "work_status": "completed",
        "start_date": start,
        "expected_completion": expected_completion,
        "actual_completion": actual_completion,
        "source": "synthetic",
    }


def make_duplicate_pair():
    p1 = make_project()
    p2 = dict(p1)
    p2["work_name"] = (p1["work_name"] + " Phase 2")[:60]
    p2["description"] = p1["description"] + ", phase 2 continuation"
    return [p1, p2]


def build_dataset(n=1500):
    n_cost = int(n * 0.03)
    n_delay = int(n * 0.05)
    n_agency = int(n * 0.04)
    n_normal = n - n_cost - n_delay - n_agency - 10

    rows = [make_project() for _ in range(n_normal)]
    rows += [make_project(force_anomaly="cost") for _ in range(n_cost)]
    rows += [make_project(force_anomaly="delay") for _ in range(n_delay)]
    rows += [make_project(force_anomaly="agency") for _ in range(n_agency)]
    for _ in range(5):
        rows.extend(make_duplicate_pair())

    random.shuffle(rows)
    return rows


def insert_rows(rows):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO projects ({', '.join(cols)}) VALUES ({placeholders})"
    for row in rows:
        cur.execute(sql, [row[c] for c in cols])
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    dataset = build_dataset()
    insert_rows(dataset)
    print(f"Inserted {len(dataset)} synthetic projects.")
```

- [ ] **Step 3: Run it and verify**

Run: `python data/generate_synthetic.py`
Expected: prints `Inserted 1500 synthetic projects.` with no errors.

Run: `psql "$DATABASE_URL" -c "SELECT count(*) FROM projects;"`
Expected: count matches (1500).

- [ ] **Step 4: Commit**

```bash
git add data/requirements.txt data/generate_synthetic.py
git commit -m "feat: add synthetic MPLADS data generator"
git push
```

---

## Task 2: Real sample data loader (Track: data, time-boxed to ~1 hour)

**Files:**
- Create: `data/load_real_sample.py`

**Interfaces:**
- Consumes: a manually downloaded CSV from the MPLADS portal or data.gov.in, `DATABASE_URL`.
- Produces: additional `projects` rows with `source='real'`; invalid rows land in `rejected_rows` instead of corrupting the table.

This task is exploratory, not TDD — the real CSV's column names are unknown until you have the file in hand. **Hard time-box: if no usable CSV is found within ~1 hour, skip this task entirely and rely on the synthetic dataset alone (spec section 3 explicitly allows this).**

- [ ] **Step 1: Find and download one CSV**

Search data.gov.in and the MPLADS portal for any downloadable project/work-level dataset (one state is enough). Save it locally, e.g. `data/raw/sample.csv`.

- [ ] **Step 2: Inspect its columns**

Run: `python -c "import pandas as pd; print(pd.read_csv('data/raw/sample.csv', nrows=0).columns.tolist())"`

- [ ] **Step 3: Write the loader, with `COLUMN_MAP` edited to match the real headers from Step 2**

```python
# data/load_real_sample.py
"""
Loads a real MPLADS/data.gov.in CSV sample into the projects table.
Usage: python load_real_sample.py path/to/downloaded.csv

Edit COLUMN_MAP's values below to match the actual CSV header names
found via Step 2 before running.
"""
import os
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

COLUMN_MAP = {
    "work_name": "Work Description",
    "mp_name": "MP Name",
    "constituency": "Constituency",
    "state": "State",
    "district": "District",
    "category": "Work Category",
    "implementing_agency": "Implementing Agency",
    "sanctioned_amount": "Sanctioned Amount",
    "expenditure": "Expenditure",
    "work_status": "Status",
}


def load(csv_path):
    df = pd.read_csv(csv_path)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    inserted, rejected = 0, 0
    for _, raw in df.iterrows():
        try:
            row = {k: raw[v] for k, v in COLUMN_MAP.items()}
            row["description"] = row["work_name"]
            row["sanctioned_amount"] = float(row["sanctioned_amount"])
            row["expenditure"] = (
                float(row["expenditure"]) if pd.notna(row["expenditure"]) else 0.0
            )
            row["recommended_amount"] = row["sanctioned_amount"]
            row["source"] = "real"
            cols = list(row.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO projects ({', '.join(cols)}) VALUES ({placeholders})",
                [row[c] for c in cols],
            )
            inserted += 1
        except (KeyError, ValueError, TypeError) as e:
            cur.execute(
                "INSERT INTO rejected_rows (raw_row, reason, source_file) VALUES (%s, %s, %s)",
                (Json(raw.dropna().to_dict()), str(e), csv_path),
            )
            rejected += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {inserted}, rejected {rejected}")


if __name__ == "__main__":
    load(sys.argv[1])
```

- [ ] **Step 4: Run it and verify**

Run: `python data/load_real_sample.py data/raw/sample.csv`
Expected: prints inserted/rejected counts with `inserted > 0`.

- [ ] **Step 5: Commit**

```bash
git add data/load_real_sample.py
git commit -m "feat: add real MPLADS CSV loader"
git push
```

If this task was skipped per the time-box, skip this commit and move on — nothing else depends on it.

---

## Task 3: Feature calculation + risk scoring (Track: data)

**Files:**
- Create: `data/scoring.py`
- Create: `data/test_scoring.py`

**Interfaces:**
- Consumes: all `projects` rows from Task 1/2.
- Produces: every `projects` column listed under "computed" and "risk scores" in Task 0's schema, filled in for every row. This is the data the API (Task 4) reads.

- [ ] **Step 1: Write the failing test first**

```python
# data/test_scoring.py
import pandas as pd
from datetime import date
from scoring import (
    compute_delay_days, cost_risk_score, delay_risk_score,
    duplicate_risk_score, agency_risk_score, risk_level,
    build_flagged_reasons,
)


def test_known_high_risk_project_lands_in_high_band():
    row = pd.Series({
        "actual_completion": date(2024, 6, 1),
        "expected_completion": date(2024, 1, 1),
        "cost_deviation_pct": 80.0,
        "max_similarity_score": 0.92,
        "agency_delay_rate": 70.0,
        "compliance_reasons": [],
    })
    row["delay_days"] = compute_delay_days(row)
    row["cost_risk"] = cost_risk_score(row)
    row["delay_risk"] = delay_risk_score(row)
    row["duplicate_risk"] = duplicate_risk_score(row)
    row["agency_risk"] = agency_risk_score(row)

    overall = (
        row["cost_risk"] * 0.25 + row["delay_risk"] * 0.25
        + row["duplicate_risk"] * 0.20 + row["agency_risk"] * 0.15
    )
    assert risk_level(overall) == "HIGH"

    reasons = build_flagged_reasons(row)
    assert any("similarity" in r for r in reasons)
    assert any("days beyond expected completion" in r for r in reasons)


def test_clean_project_lands_in_low_band():
    row = pd.Series({
        "actual_completion": date(2024, 1, 5),
        "expected_completion": date(2024, 1, 1),
        "cost_deviation_pct": 2.0,
        "max_similarity_score": 0.1,
        "agency_delay_rate": 5.0,
        "compliance_reasons": [],
    })
    row["delay_days"] = compute_delay_days(row)
    row["cost_risk"] = cost_risk_score(row)
    row["delay_risk"] = delay_risk_score(row)
    row["duplicate_risk"] = duplicate_risk_score(row)
    row["agency_risk"] = agency_risk_score(row)

    overall = (
        row["cost_risk"] * 0.25 + row["delay_risk"] * 0.25
        + row["duplicate_risk"] * 0.20 + row["agency_risk"] * 0.15
    )
    assert risk_level(overall) == "LOW"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd data && python -m pytest test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scoring'` (scoring.py doesn't exist yet).

- [ ] **Step 3: Write the scoring module**

```python
# data/scoring.py
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
    scored = score_dataframe(df)
    write_scores(conn, scored)
    print(f"Scored {len(scored)} projects.")
    conn.close()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd data && python -m pytest test_scoring.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Run the batch scoring job against the real database**

Run: `python data/scoring.py`
Expected: prints `Scored 1500 projects.` (or however many rows exist).

Run: `psql "$DATABASE_URL" -c "SELECT risk_level, count(*) FROM projects GROUP BY risk_level;"`
Expected: all three of LOW/MEDIUM/HIGH present, HIGH count roughly matching the seeded anomaly rate from Task 1.

- [ ] **Step 6: Commit**

```bash
git add data/scoring.py data/test_scoring.py
git commit -m "feat: add risk scoring engine with rules, Isolation Forest, and duplicate detection"
git push
```

---

## Task 4: FastAPI backend (Track: api)

**Files:**
- Create: `api/requirements.txt`
- Create: `api/db.py`
- Create: `api/main.py`
- Create: `api/test_api.py`

**Interfaces:**
- Consumes: `DATABASE_URL` from root `.env`, the fully-scored `projects` table (Task 3 must have run at least once against the same database before this task's tests will pass).
- Produces: `GET /api/overview`, `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/map/states`, `GET /api/agencies`, `GET /api/districts` — the exact shapes Task 5–8 (web) consume.

- [ ] **Step 1: Write requirements and the DB helper**

```
# api/requirements.txt
fastapi
uvicorn
psycopg2-binary
python-dotenv
httpx
```

```python
# api/db.py
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def query(sql, params=None, one=False):
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()
```

- [ ] **Step 2: Write the app**

```python
# api/main.py
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from db import query

app = FastAPI(title="MPLADS Risk Monitor API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)


@app.get("/api/overview")
def overview():
    return query(
        """
        SELECT
          COUNT(*) AS total_projects,
          COALESCE(SUM(expenditure), 0) AS total_expenditure,
          COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count,
          COUNT(*) FILTER (WHERE delay_days > 60) AS delayed_count,
          COUNT(*) FILTER (WHERE overall_risk_score > 40) AS anomaly_count
        FROM projects
        """,
        one=True,
    )


@app.get("/api/projects")
def list_projects(
    state: Optional[str] = None,
    district: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    filters, params = [], []
    if state:
        filters.append("state = %s")
        params.append(state)
    if district:
        filters.append("district = %s")
        params.append(district)
    if risk_level:
        filters.append("risk_level = %s")
        params.append(risk_level)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    params += [limit, offset]

    return query(
        f"""
        SELECT id, work_name, state, district, category, implementing_agency,
               sanctioned_amount, overall_risk_score, risk_level
        FROM projects
        {where}
        ORDER BY overall_risk_score DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        params,
    )


@app.get("/api/projects/{project_id}")
def project_detail(project_id: int):
    row = query("SELECT * FROM projects WHERE id = %s", [project_id], one=True)
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


@app.get("/api/map/states")
def map_states():
    return query(
        """
        SELECT state,
               COUNT(*) AS total_projects,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count,
               COALESCE(AVG(overall_risk_score), 0) AS avg_risk_score
        FROM projects GROUP BY state
        """
    )


@app.get("/api/agencies")
def agencies():
    return query(
        """
        SELECT implementing_agency,
               COUNT(*) AS total_projects,
               COUNT(*) FILTER (WHERE delay_days > 60) AS delayed_count,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS anomaly_count,
               COALESCE(AVG(overall_risk_score), 0) AS avg_risk_score
        FROM projects GROUP BY implementing_agency
        ORDER BY avg_risk_score DESC
        """
    )


@app.get("/api/districts")
def districts():
    return query(
        """
        SELECT state, district,
               COUNT(*) AS total_projects,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count,
               COALESCE(AVG(overall_risk_score), 0) AS avg_risk_score
        FROM projects GROUP BY state, district
        ORDER BY avg_risk_score DESC
        """
    )
```

- [ ] **Step 3: Write the smoke tests**

```python
# api/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_overview_returns_totals():
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    assert resp.json()["total_projects"] > 0


def test_projects_list_returns_200_and_list():
    resp = client.get("/api/projects?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_project_detail_404_for_unknown_id():
    resp = client.get("/api/projects/999999999")
    assert resp.status_code == 404


def test_map_states_returns_200():
    resp = client.get("/api/map/states")
    assert resp.status_code == 200
```

- [ ] **Step 4: Run tests (requires Task 3 already scored the database)**

Run: `cd api && pip install -r requirements.txt && python -m pytest test_api.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Run the server locally and spot-check**

Run: `cd api && uvicorn main:app --reload --port 8000`
Then in another shell: `curl localhost:8000/api/overview`
Expected: JSON with `total_projects`, `total_expenditure`, etc.

- [ ] **Step 6: Commit**

```bash
git add api/requirements.txt api/db.py api/main.py api/test_api.py
git commit -m "feat: add read-only FastAPI backend over scored projects"
git push
```

---

## Task 5: Next.js scaffold + API client + overview screen (Track: web)

**Files:**
- Create: `web/` (scaffolded)
- Create: `web/lib/api.ts`
- Create: `web/app/layout.tsx`
- Modify: `web/app/page.tsx`

**Interfaces:**
- Consumes: `NEXT_PUBLIC_API_BASE_URL` env var, the endpoints from Task 4.
- Produces: `api` client object and its exported types (`Overview`, `ProjectSummary`, `ProjectDetail`, `StateStat`, `AgencyStat`) that Tasks 6–8 import from `@/lib/api`.

- [ ] **Step 1: Scaffold the app**

Run: `npx create-next-app@latest web --typescript --tailwind --app --no-src-dir --import-alias "@/*" --eslint --yes`

- [ ] **Step 2: Set the API base URL**

```bash
# web/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 3: Write the API client**

```typescript
// web/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Overview = {
  total_projects: number;
  total_expenditure: number;
  high_risk_count: number;
  delayed_count: number;
  anomaly_count: number;
};

export type ProjectSummary = {
  id: number;
  work_name: string;
  state: string;
  district: string;
  category: string;
  implementing_agency: string;
  sanctioned_amount: number;
  overall_risk_score: number | null;
  risk_level: string | null;
};

export type ProjectDetail = ProjectSummary & {
  description: string;
  mp_name: string;
  constituency: string;
  cost_risk: number;
  delay_risk: number;
  duplicate_risk: number;
  agency_risk: number;
  compliance_risk: number;
  flagged_reasons: string[];
  delay_days: number;
  cost_deviation_pct: number;
  similar_work_id: number | null;
};

export type StateStat = {
  state: string;
  total_projects: number;
  high_risk_count: number;
  avg_risk_score: number;
};

export type AgencyStat = {
  implementing_agency: string;
  total_projects: number;
  delayed_count: number;
  anomaly_count: number;
  avg_risk_score: number;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  projects: (params: Record<string, string> = {}) =>
    get<ProjectSummary[]>(`/api/projects?${new URLSearchParams(params)}`),
  project: (id: number) => get<ProjectDetail>(`/api/projects/${id}`),
  mapStates: () => get<StateStat[]>("/api/map/states"),
  agencies: () => get<AgencyStat[]>("/api/agencies"),
};
```

- [ ] **Step 4: Write the nav layout**

```tsx
// web/app/layout.tsx
import "./globals.css";
import Link from "next/link";

export const metadata = { title: "MPLADS Risk Monitor" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="flex gap-4 p-4 border-b">
          <Link href="/">Overview</Link>
          <Link href="/map">Risk Map</Link>
          <Link href="/projects">Projects</Link>
          <Link href="/analysis">Agency Analysis</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Write the overview screen**

```tsx
// web/app/page.tsx
import { api } from "@/lib/api";

export default async function OverviewPage() {
  const data = await api.overview();
  const cards = [
    { label: "Total Projects", value: data.total_projects },
    { label: "Total Expenditure", value: `₹${Number(data.total_expenditure).toLocaleString("en-IN")}` },
    { label: "High-Risk Projects", value: data.high_risk_count },
    { label: "Delayed Projects", value: data.delayed_count },
    { label: "Anomalies", value: data.anomaly_count },
  ];
  return (
    <main className="p-8 grid grid-cols-2 md:grid-cols-5 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-lg border p-4">
          <div className="text-sm text-gray-500">{c.label}</div>
          <div className="text-2xl font-semibold">{c.value}</div>
        </div>
      ))}
    </main>
  );
}
```

- [ ] **Step 6: Run it and manually verify**

Run: `cd web && npm run dev` (with `api/main.py` also running per Task 4 Step 5)
Open `http://localhost:3000` — expected: 5 stat cards with real, non-zero numbers matching `curl localhost:8000/api/overview`.

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "feat: scaffold Next.js dashboard with overview screen"
git push
```

---

## Task 6: Risk map screen (Track: web)

**Files:**
- Create: `web/public/india-states.geojson`
- Create: `web/app/map/page.tsx`
- Modify: `web/package.json` (add `leaflet`, `react-leaflet`)

**Interfaces:**
- Consumes: `api.mapStates()` and its `StateStat` type from Task 5.

- [ ] **Step 1: Install map dependencies**

Run: `cd web && npm install leaflet react-leaflet && npm install -D @types/leaflet`

- [ ] **Step 2: Get an India states GeoJSON**

Download a public India state-boundary GeoJSON into `web/public/india-states.geojson`. Inspect one feature's `properties` to find the state-name field (commonly `NAME_1` or `st_nm`) — you need this key to match against `StateStat.state` in Step 4.

If no usable GeoJSON is found quickly, skip the `MapContainer`/`GeoJSON` block in Step 4 entirely and ship the table alone — the table is the reliability fallback, not a stretch feature.

- [ ] **Step 3: Add Leaflet's CSS**

```tsx
// web/app/layout.tsx — add this import at the top, alongside "./globals.css"
import "leaflet/dist/leaflet.css";
```

- [ ] **Step 4: Write the map screen**

```tsx
// web/app/map/page.tsx
"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api, StateStat } from "@/lib/api";

const MapContainer = dynamic(() => import("react-leaflet").then((m) => m.MapContainer), { ssr: false });
const GeoJSON = dynamic(() => import("react-leaflet").then((m) => m.GeoJSON), { ssr: false });

function riskColor(score: number) {
  if (score > 70) return "#dc2626";
  if (score > 40) return "#f59e0b";
  return "#16a34a";
}

export default function MapPage() {
  const [stats, setStats] = useState<StateStat[]>([]);
  const [geojson, setGeojson] = useState<any>(null);

  useEffect(() => {
    api.mapStates().then(setStats);
    fetch("/india-states.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then(setGeojson)
      .catch(() => setGeojson(null));
  }, []);

  const byState = Object.fromEntries(stats.map((s) => [s.state, s]));

  return (
    <main className="p-8">
      <h1 className="text-xl font-semibold mb-4">Risk by State</h1>

      {geojson && (
        <div style={{ height: 500 }} className="mb-6">
          <MapContainer center={[22.5, 80]} zoom={5} style={{ height: "100%", width: "100%" }}>
            <GeoJSON
              data={geojson}
              style={(feature: any) => {
                const name = feature.properties.NAME_1 ?? feature.properties.st_nm;
                const stat = byState[name];
                return {
                  fillColor: stat ? riskColor(stat.avg_risk_score) : "#e5e7eb",
                  fillOpacity: 0.7,
                  color: "#374151",
                  weight: 1,
                };
              }}
            />
          </MapContainer>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>State</th>
            <th>Projects</th>
            <th>High Risk</th>
            <th>Avg Score</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.state} className="border-b">
              <td>{s.state}</td>
              <td>{s.total_projects}</td>
              <td>{s.high_risk_count}</td>
              <td>{s.avg_risk_score.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 5: Run it and manually verify**

Open `http://localhost:3000/map`. Expected: the state table always renders with real numbers; the choropleth renders too if Step 2's GeoJSON property names matched the DB's state names (check visually — states should be colored, not all grey).

- [ ] **Step 6: Commit**

```bash
git add web/
git commit -m "feat: add state-level risk map screen"
git push
```

---

## Task 7: Project list + investigation screen (Track: web)

**Files:**
- Create: `web/app/projects/page.tsx`
- Create: `web/app/projects/[id]/page.tsx`

**Interfaces:**
- Consumes: `api.projects()`, `api.project(id)`, `ProjectSummary`, `ProjectDetail` from Task 5.

- [ ] **Step 1: Write the project list screen**

```tsx
// web/app/projects/page.tsx
import Link from "next/link";
import { api } from "@/lib/api";

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Record<string, string>;
}) {
  const projects = await api.projects(searchParams);
  return (
    <main className="p-8">
      <h1 className="text-xl font-semibold mb-4">Projects</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>Work</th>
            <th>State</th>
            <th>District</th>
            <th>Agency</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.id} className="border-b hover:bg-gray-50">
              <td>
                <Link href={`/projects/${p.id}`} className="underline">
                  {p.work_name}
                </Link>
              </td>
              <td>{p.state}</td>
              <td>{p.district}</td>
              <td>{p.implementing_agency}</td>
              <td>
                {p.risk_level} ({p.overall_risk_score?.toFixed(0)})
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 2: Write the project investigation screen**

```tsx
// web/app/projects/[id]/page.tsx
import { api } from "@/lib/api";

export default async function ProjectPage({ params }: { params: { id: string } }) {
  const p = await api.project(Number(params.id));
  const components = [
    { label: "Cost", value: p.cost_risk },
    { label: "Delay", value: p.delay_risk },
    { label: "Duplicate", value: p.duplicate_risk },
    { label: "Agency", value: p.agency_risk },
    { label: "Compliance", value: p.compliance_risk },
  ];
  return (
    <main className="p-8 max-w-2xl">
      <h1 className="text-xl font-semibold">{p.work_name}</h1>
      <p className="text-sm text-gray-500 mb-4">
        {p.state} / {p.district} — {p.implementing_agency}
      </p>

      <div className="text-3xl font-bold mb-4">
        Risk Score: {p.overall_risk_score?.toFixed(0)}/100 ({p.risk_level})
      </div>

      <ul className="mb-4">
        {components.map((c) => (
          <li key={c.label}>
            {c.label}: {c.value?.toFixed(0)}
          </li>
        ))}
      </ul>

      <h2 className="font-semibold mb-2">Why was this flagged?</h2>
      <ul className="list-disc pl-5">
        {p.flagged_reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>

      {p.similar_work_id && (
        <p className="mt-4 text-sm">
          Similar to{" "}
          <a className="underline" href={`/projects/${p.similar_work_id}`}>
            project #{p.similar_work_id}
          </a>
        </p>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Run it and manually verify**

Open `http://localhost:3000/projects` — expected: table sorted by risk descending. Click a HIGH-risk row — expected: detail page shows a score, 5 component risks, and a non-empty "why flagged" list matching the row's `flagged_reasons`.

- [ ] **Step 4: Commit**

```bash
git add web/app/projects
git commit -m "feat: add project list and investigation screens"
git push
```

---

## Task 8: Agency/district analysis screen (Track: web)

**Files:**
- Create: `web/app/analysis/page.tsx`

**Interfaces:**
- Consumes: `api.agencies()`, `AgencyStat` from Task 5.

- [ ] **Step 1: Write the screen**

```tsx
// web/app/analysis/page.tsx
import { api } from "@/lib/api";

export default async function AnalysisPage() {
  const agencies = await api.agencies();
  return (
    <main className="p-8">
      <h1 className="text-xl font-semibold mb-4">Agency Analysis</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>Agency</th>
            <th>Projects</th>
            <th>Delayed</th>
            <th>Anomalies</th>
            <th>Avg Risk</th>
          </tr>
        </thead>
        <tbody>
          {agencies.map((a) => (
            <tr key={a.implementing_agency} className="border-b">
              <td>{a.implementing_agency}</td>
              <td>{a.total_projects}</td>
              <td>{a.delayed_count}</td>
              <td>{a.anomaly_count}</td>
              <td>{a.avg_risk_score.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 2: Run it and manually verify**

Open `http://localhost:3000/analysis` — expected: "Agency X" (the deliberately seeded bad agency from Task 1) shows a visibly higher delayed/anomaly count and avg risk than the others.

- [ ] **Step 3: Commit**

```bash
git add web/app/analysis
git commit -m "feat: add agency analysis screen"
git push
```

---

## Task 9: Deployment (shared, after Tasks 4 and 5-8 land)

**Files:**
- Create: `api/vercel.json` (if the current Vercel Python pattern needs it — confirm via the skill in Step 1)
- Modify: Vercel project env vars (no local file)

**Interfaces:**
- Consumes: `DATABASE_URL` (Task 0), the working `api/` app (Task 4), the working `web/` app (Tasks 5-8).
- Produces: two deployed Vercel URLs — one for the API, one for the dashboard, wired together.

- [ ] **Step 1: Deploy the API**

Invoke the `vercel:vercel-functions` skill for the current zero-config (or minimal-config) pattern for deploying a Python/FastAPI ASGI app on Vercel, then deploy `api/` as its own Vercel project following it. Set `DATABASE_URL` as an env var on that project (use the `vercel:env-vars` skill or `vercel env add DATABASE_URL`).

Verify: `curl https://<api-project>.vercel.app/api/overview` returns the same JSON as local.

- [ ] **Step 2: Deploy the web app**

Set `NEXT_PUBLIC_API_BASE_URL` to the deployed API URL from Step 1 (as a Vercel env var on the `web` project, and update `web/.env.local` for continued local dev against the deployed API if useful). Deploy `web/` per the `vercel:deploy` skill.

Verify: open the deployed web URL, click through all 4 screens, confirm real data loads (not `localhost` errors).

- [ ] **Step 3: Commit any config changes**

```bash
git add api/vercel.json web/.env.local
git commit -m "chore: wire up Vercel deployment for api and web"
git push
```

---

## Task 10: Final integration / demo dry run (shared, last)

**Files:** none — verification only.

- [ ] **Step 1: Re-run the full pipeline end to end on the deployed database**

Run: `python data/generate_synthetic.py && python data/scoring.py` (against the same `DATABASE_URL` the deployed API uses), confirming fresh data flows through without manual DB edits.

- [ ] **Step 2: Click through all 4 screens on the deployed URL**

Overview → Risk Map → a HIGH-risk project's investigation page → Agency Analysis. Confirm every number is real (not placeholder/zero) and the "why flagged" bullets read coherently against the project's actual state.

- [ ] **Step 3: Note any rough edges as a short list**

Anything visibly broken or confusing goes in a plain list in the PR/commit description — not fixed silently at this stage unless it's a one-line fix.

---

## Addendum — follow-up tasks from the 2026-08-31 data (Track: data)

Tasks 0–10 are complete and deployed. These follow from the two-term extract;
see spec §14 for the measurements behind each. They are independent of each
other and none of them block the demo.

### Task 11: Derive a sector and fix the cost baseline

Spec §14.3. `scoring.py` groups cost deviation by `(district, category)`, and
`category` is one value for 98.1% of rows, so the baseline mixes street lights
with roads.

- [ ] Add a keyword classifier over `work_description` producing a `sector`
      column (a prototype reaches 82.9% coverage; rules are ordered, first match
      wins, so lighting is tested before roads).
- [ ] Group `district_avg_cost` on `(district, sector)`; prefer the median over
      the mean, since a single ₹7.5 crore work drags a district mean badly.
- [ ] Add a minimum peer count below which `cost_risk` scores 0, and guard the
      "cost is N% above similar projects" reason on the same threshold so no
      explanation quotes a comparison group too thin to show.
- [ ] Verify: the highest-scoring works should change, and each should be
      checkable by hand against the CSV.

### Task 12: Score vendor concentration at the agency grain

Spec §14.4. `load_real_data.py` already says the expenditure file is kept for
this.

- [ ] Load `mplads_expenditures_*.csv` into its own table at its own grain — it
      does not join to works (spec §14.2), so do not attempt to attach it to
      `projects`.
- [ ] Per `(IDA, ls_term)`: vendor count, Herfindahl index of vendor share of
      spend, largest vendor and its share, count and age of in-progress payments.
- [ ] Feed that into `agency_risk` alongside the existing delay rate, and surface
      it on the agency analysis screen with the reason text spelled out.
- [ ] Verify: an agency flagged for concentration should be traceable to specific
      vendor rows in the CSV.

### Task 13: Normalize MP identity

Spec §14.4. Only needed if MP-level aggregates are added; the current dashboard
does not group by MP.

- [ ] Derive an `mp_id` from a normalized name (strip the term marker and
      honorifics, casefold, collapse whitespace) plus state and house.
- [ ] Verify: distinct `mp_id` per term should be 773 for LS17 and 774 for LS18,
      and every work's `mp_id` should exist in the MP summary.
