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
ALTER TABLE projects ADD COLUMN IF NOT EXISTS peer_median_cost NUMERIC(14,2);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS peer_count INTEGER;
ALTER TABLE projects DROP COLUMN IF EXISTS district_avg_cost;

CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);
CREATE INDEX IF NOT EXISTS idx_projects_sector ON projects(sector);
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
