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
    -- What the MP has committed to works. Added 2026-09-09, when the source
    -- began publishing it; it is the numerator of the utilisation figure its
    -- own dashboard shows.
    amount_recommended NUMERIC(16,2),
    -- NOT "allocation not used". The source renamed this column to
    -- "Balance Not Yet Paid to Vendors" and the name is the accurate one:
    -- across all 1,548 rows it equals amount_recommended - total_expenditure
    -- exactly, and equals allocated_amount - total_expenditure on only 39.
    -- Money committed to works but not yet paid out is a far weaker finding
    -- than money never committed at all - see idle_allocation in
    -- data/detectors.py, which now computes the latter itself.
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
-- Added 2026-09-07. See data/load_real_data.py:work_key. Unique only where it
-- is set, so synthetic rows (which have no source Work ID) are unaffected.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS work_key TEXT;
-- Added 2026-09-07, see the column comment above.
-- Added 2026-09-09. Every derived column moved to project_scores; see the
-- note on that table for why. Dropping them here is what stops `projects`
-- being rewritten by each scoring run.
ALTER TABLE projects
    DROP COLUMN IF EXISTS delay_days,
    DROP COLUMN IF EXISTS cost_deviation_pct,
    DROP COLUMN IF EXISTS expenditure_ratio,
    DROP COLUMN IF EXISTS sector,
    DROP COLUMN IF EXISTS peer_median_cost,
    DROP COLUMN IF EXISTS peer_count,
    DROP COLUMN IF EXISTS agency_delay_rate,
    DROP COLUMN IF EXISTS max_similarity_score,
    DROP COLUMN IF EXISTS similar_work_id,
    DROP COLUMN IF EXISTS cost_risk,
    DROP COLUMN IF EXISTS delay_risk,
    DROP COLUMN IF EXISTS duplicate_risk,
    DROP COLUMN IF EXISTS agency_risk,
    DROP COLUMN IF EXISTS compliance_risk,
    DROP COLUMN IF EXISTS overall_risk_score,
    DROP COLUMN IF EXISTS risk_level,
    DROP COLUMN IF EXISTS flagged_reasons,
    DROP COLUMN IF EXISTS district_avg_cost;

-- Added 2026-09-09 with the source's new column. See the note on mps.
ALTER TABLE mps ADD COLUMN IF NOT EXISTS amount_recommended NUMERIC(16,2);
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_work_key
    ON projects(work_key) WHERE work_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);
CREATE INDEX IF NOT EXISTS idx_expenditures_agency ON expenditures(implementing_agency, ls_term);
CREATE INDEX IF NOT EXISTS idx_expenditures_vendor ON expenditures(vendor);
CREATE INDEX IF NOT EXISTS idx_projects_mp_id ON projects(mp_id);
CREATE INDEX IF NOT EXISTS idx_projects_ls_term ON projects(ls_term);
CREATE INDEX IF NOT EXISTS idx_mps_name ON mps(mp_name);
CREATE INDEX IF NOT EXISTS idx_projects_district ON projects(district);
CREATE INDEX IF NOT EXISTS idx_projects_agency ON projects(implementing_agency);


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


-- Cohort-level detector findings (data/detectors.py). One row per finding, and
-- a finding describes an agency or an MP rather than a work: these are
-- population statistics, and attributing one to whichever work happened to be
-- in the population is the mistake that makes a risk score unusable in a
-- hearing. Nothing here feeds overall_risk_score.
--
-- Rebuilt from scratch on every scoring run, like agency_vendor_profile.
CREATE TABLE IF NOT EXISTS detector_findings (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,              -- 'D-01' .. 'D-04'
    subject_type TEXT NOT NULL,      -- 'agency' | 'mp'
    subject TEXT NOT NULL,           -- implementing agency name, or mp_id
    ls_term SMALLINT,
    period TEXT,                     -- fiscal year for D-01, else NULL
    severity NUMERIC(5,2) NOT NULL,
    headline TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_detector_findings_code ON detector_findings(code);
CREATE INDEX IF NOT EXISTS idx_detector_findings_subject
    ON detector_findings(subject_type, subject, ls_term);
CREATE INDEX IF NOT EXISTS idx_detector_findings_severity
    ON detector_findings(severity DESC);


-- Append-only trail of every decision recorded against a work.
--
-- work_reviews holds only the current verdict, so changing a decision
-- overwrote the note that explained the previous one: escalate a work with a
-- reason, dismiss it later without one, and the reason is gone. For a queue
-- whose whole output is "an official looked at this and concluded X", losing
-- the earlier X is losing the audit trail.
--
-- Nothing here is ever updated or deleted. Keyed on work_key for the same
-- reason work_reviews is: projects.id is reassigned on every reload.
CREATE TABLE IF NOT EXISTS work_review_events (
    id BIGSERIAL PRIMARY KEY,
    work_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('verified', 'dismissed', 'escalated')),
    note TEXT,
    reviewer TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_work_review_events_work_key
    ON work_review_events(work_key, created_at DESC);


-- Scores live apart from the works they describe.
--
-- Scoring used to UPDATE all 250,839 rows of `projects` in one statement.
-- Postgres writes a new version of every row an UPDATE touches, so each run
-- doubled the table - 161 MB to 280 MB, taking the database from 300 MB to
-- 457 MB against Neon's 512 MB limit. The space only comes back with a
-- VACUUM FULL, which needs room for a whole copy of the table at exactly the
-- moment there is none.
--
-- Written with TRUNCATE + INSERT instead, which reclaims in the same
-- statement, so this table is always the size of its contents and `projects`
-- is never rewritten after the load. Same contract as agency_vendor_profile
-- and detector_findings: derived, rebuilt every run, no history to keep.
CREATE TABLE IF NOT EXISTS project_scores (
    project_id INTEGER PRIMARY KEY,
    delay_days INTEGER,
    cost_deviation_pct NUMERIC(12,2),
    expenditure_ratio NUMERIC(6,2),
    sector TEXT,
    peer_median_cost NUMERIC(14,2),
    peer_count INTEGER,
    agency_delay_rate NUMERIC(5,2),
    max_similarity_score NUMERIC(5,4),
    similar_work_id INTEGER,
    cost_risk NUMERIC(5,2),
    delay_risk NUMERIC(5,2),
    duplicate_risk NUMERIC(5,2),
    agency_risk NUMERIC(5,2),
    compliance_risk NUMERIC(5,2),
    overall_risk_score NUMERIC(5,2),
    risk_level TEXT,
    flagged_reasons JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_project_scores_overall
    ON project_scores(overall_risk_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_project_scores_level ON project_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_project_scores_sector ON project_scores(sector);

-- Everything reads this rather than either table. Column names match what
-- `projects` used to carry, so the queries did not have to change shape.
-- LEFT JOIN: a work loaded but not yet scored still appears, with nulls, which
-- is what the "scoring pending" states in the interface are for.
CREATE OR REPLACE VIEW projects_scored AS
SELECT p.id, p.work_key, p.work_name, p.description, p.ls_term, p.mp_name,
       p.mp_id, p.house, p.constituency, p.state, p.district, p.category,
       p.implementing_agency, p.recommended_amount, p.sanctioned_amount,
       p.expenditure, p.work_status, p.start_date, p.expected_completion,
       p.actual_completion, p.source, p.has_images, p.created_at,
       s.delay_days, s.cost_deviation_pct, s.expenditure_ratio, s.sector,
       s.peer_median_cost, s.peer_count, s.agency_delay_rate,
       s.max_similarity_score, s.similar_work_id, s.cost_risk, s.delay_risk,
       s.duplicate_risk, s.agency_risk, s.compliance_risk,
       s.overall_risk_score, s.risk_level,
       COALESCE(s.flagged_reasons, '[]'::jsonb) AS flagged_reasons
FROM projects p
LEFT JOIN project_scores s ON s.project_id = p.id;
