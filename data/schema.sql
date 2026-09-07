-- data/schema.sql
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    -- '<Work ID>|<ls_term>|<IDA>'. The only identifier that survives a refresh:
    -- load_real_data.py deletes and re-inserts every real row, so `id` is a new
    -- number each night. Anything that has to outlive a reload keys on this.
    work_key TEXT,
    work_name TEXT NOT NULL,
    description TEXT,
    ls_term SMALLINT,
    mp_name TEXT,
    mp_id TEXT,
    house TEXT,
    constituency TEXT,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    category TEXT NOT NULL,
    sector TEXT,
    implementing_agency TEXT NOT NULL,
    recommended_amount NUMERIC(14,2),
    sanctioned_amount NUMERIC(14,2) NOT NULL,
    expenditure NUMERIC(14,2) NOT NULL DEFAULT 0,
    work_status TEXT NOT NULL,
    start_date DATE,
    expected_completion DATE,
    actual_completion DATE,
    source TEXT NOT NULL DEFAULT 'synthetic',
    has_images BOOLEAN,

    delay_days INTEGER,
    cost_deviation_pct NUMERIC(6,2),
    expenditure_ratio NUMERIC(6,2),
    peer_median_cost NUMERIC(14,2),
    peer_count INTEGER,
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

-- One row per MP per Lok Sabha term, straight from the source's own MP summary
-- extract. These are Empowered Indian's published aggregates, not ours, which
-- is what makes a utilisation figure here checkable against their site.
CREATE TABLE IF NOT EXISTS mps (
    mp_id TEXT NOT NULL,
    ls_term SMALLINT NOT NULL,
    mp_name TEXT NOT NULL,
    constituency TEXT,
    state TEXT,
    house TEXT,
    allocated_amount NUMERIC(16,2),
    total_expenditure NUMERIC(16,2),
    utilization_pct NUMERIC(6,2),
    completed_works INTEGER,
    recommended_works INTEGER,
    completion_rate_pct NUMERIC(6,2),
    unspent_amount NUMERIC(16,2),
    transaction_count INTEGER,
    successful_payments INTEGER,
    pending_payments INTEGER,
    PRIMARY KEY (mp_id, ls_term)
);

-- Expenditure transactions, at their own grain. They do NOT join to a work:
-- the file has no Work ID and its Work Description holds one of 119 coarse
-- category labels across all 270,934 rows. Kept raw so a concentration flag on
-- an agency can be traced back to the payments behind it.
CREATE TABLE IF NOT EXISTS expenditures (
    id SERIAL PRIMARY KEY,
    ls_term SMALLINT,
    mp_name TEXT,
    constituency TEXT,
    state TEXT,
    work_type_text TEXT,
    vendor TEXT NOT NULL,
    implementing_agency TEXT NOT NULL,
    district TEXT NOT NULL,
    expenditure_amount NUMERIC(16,2) NOT NULL,
    expenditure_date DATE,
    payment_status TEXT NOT NULL
);

-- One row per implementing agency, derived from expenditures by
-- data/vendors.py. Rebuilt from scratch on every scoring run.
CREATE TABLE IF NOT EXISTS agency_vendor_profile (
    implementing_agency TEXT NOT NULL,
    ls_term SMALLINT NOT NULL,
    vendor_count INTEGER NOT NULL,
    transaction_count INTEGER NOT NULL,
    total_spend NUMERIC(18,2) NOT NULL,
    vendor_hhi NUMERIC(6,4) NOT NULL,
    top_vendor TEXT,
    top_vendor_share_pct NUMERIC(5,2),
    pending_count INTEGER NOT NULL DEFAULT 0,
    oldest_pending_days INTEGER NOT NULL DEFAULT 0,
    concentration_risk NUMERIC(5,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (implementing_agency, ls_term)
);

CREATE TABLE IF NOT EXISTS rejected_rows (
    id SERIAL PRIMARY KEY,
    raw_row JSONB NOT NULL,
    reason TEXT NOT NULL,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Added 2026-08-31. Cost peers are (district, sector), not (district, category):
-- category is 'Normal/Others' for 98.1% of rows and never stratified anything.
-- ALTER ... IF (NOT) EXISTS so this file stays runnable against a database that
-- already holds the old shape. district_avg_cost is dropped rather than kept:
-- it is recomputed from scratch on every scoring run and nothing reads it
-- outside scoring.py, so there is no history to preserve.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS sector TEXT;
-- Added 2026-08-31. mp_name is not a key: 1,262 name strings for ~774 MPs per
-- term, because the source appends term markers and varies honorifics. mp_id
-- is derived by data/mps.py. house is carried because the same name in the
-- same state can belong to a Lok Sabha and a Rajya Sabha member.
-- Added 2026-08-31. Works from both Lok Sabha terms live in one table and
-- were indistinguishable, so every per-agency and per-MP aggregate had to pool
-- them. Work IDs also restart per term, which makes (work_id, ls_term) the
-- natural key even though the surrogate id is the primary one.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS ls_term SMALLINT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS mp_id TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS house TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS peer_median_cost NUMERIC(14,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS peer_count INTEGER;
ALTER TABLE projects DROP COLUMN IF EXISTS district_avg_cost;
-- Added 2026-09-07. See data/load_real_data.py:work_key. Unique only where it
-- is set, so synthetic rows (which have no source Work ID) are unaffected.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS work_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_work_key
    ON projects(work_key) WHERE work_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);
CREATE INDEX IF NOT EXISTS idx_projects_sector ON projects(sector);
CREATE INDEX IF NOT EXISTS idx_expenditures_agency ON expenditures(implementing_agency, ls_term);
CREATE INDEX IF NOT EXISTS idx_expenditures_vendor ON expenditures(vendor);
CREATE INDEX IF NOT EXISTS idx_projects_mp_id ON projects(mp_id);
CREATE INDEX IF NOT EXISTS idx_projects_ls_term ON projects(ls_term);
CREATE INDEX IF NOT EXISTS idx_mps_name ON mps(mp_name);
CREATE INDEX IF NOT EXISTS idx_projects_district ON projects(district);
CREATE INDEX IF NOT EXISTS idx_projects_agency ON projects(implementing_agency);
CREATE INDEX IF NOT EXISTS idx_projects_risk_level ON projects(risk_level);

-- Required, not an optimisation. similar_work_id carries a self-referencing FK
-- to projects(id); without an index on the referencing column, deleting N rows
-- makes Postgres scan the whole table once per deleted row to check the
-- constraint. At 127k rows that is ~1.6e10 comparisons and the reload in
-- load_real_data.py never finishes. With this index the same delete is instant.
CREATE INDEX IF NOT EXISTS idx_projects_similar_work_id ON projects(similar_work_id);

-- Audit trail for load_real_data.py / scoring.py runs. Also what the UI's
-- freshness indicator reads (GET /api/data-freshness) — see task-12.
CREATE TABLE IF NOT EXISTS data_refresh (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,            -- 'running' | 'success' | 'failed'
    rows_loaded INTEGER,
    rows_scored INTEGER,
    rows_rejected INTEGER,
    source TEXT,                     -- where the data came from this run
    notes TEXT
);


-- Reviewer triage state for the alert queue: which flagged works someone has
-- actually looked at, and what they concluded. Absence of a row means
-- 'pending', so this holds decisions (thousands) rather than a placeholder per
-- work (127k+).
--
-- Keyed on work_key, NOT projects.id. The nightly reload deletes every real row
-- and re-inserts it, so a review pinned to a serial id would silently reattach
-- itself to an unrelated work the next morning. No foreign key for the same
-- reason: the referenced row is legitimately absent between the DELETE and the
-- INSERT, and a work can also disappear from a later snapshot entirely.
CREATE TABLE IF NOT EXISTS work_reviews (
    work_key TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('verified', 'dismissed', 'escalated')),
    note TEXT,
    reviewer TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_work_reviews_status ON work_reviews(status);
