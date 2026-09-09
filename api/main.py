import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from db import execute, query

app = FastAPI(title="MPLADS Risk Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/overview")
def overview(ls_term: Optional[int] = Query(None, ge=17, le=18)):
    """Headline figures, optionally for one Lok Sabha term.

    The term matters for comparison as much as for correctness. The source's
    own dashboard defaults to a single term, so pooling both here produced
    figures that looked wrong next to it while being right - our completed
    works came to Rs 6,340 Cr across both terms against their Rs 2,408 Cr for
    the 18th alone.

    Three different money figures live in this record and they are not
    interchangeable:
      - completed_works_value: what completed works finally cost. This is the
        one that reconciles with the source's completedWorksValue.
      - sanctioned_total: what has been sanctioned, completed or not.
      - vendor_payments: what the expenditure extract records actually being
        paid out. This is what the source's dashboard calls "Total
        Expenditure".
    """
    where, params = ("WHERE ls_term = %s", [ls_term]) if ls_term else ("", [])
    row = query(
        f"""
        SELECT
          COUNT(*) AS total_projects,
          COUNT(*) FILTER (WHERE work_status = 'completed') AS completed_count,
          COUNT(*) FILTER (WHERE work_status = 'recommended') AS pending_count,
          COALESCE(SUM(expenditure), 0) AS total_expenditure,
          COALESCE(SUM(expenditure) FILTER (WHERE work_status = 'completed'), 0)
            AS completed_works_value,
          COALESCE(SUM(sanctioned_amount), 0) AS sanctioned_total,
          COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count,
          COUNT(*) FILTER (WHERE delay_days > 60) AS delayed_count,
          -- >= 40, not > 40. The alert queue's threshold is inclusive (it is
          -- where risk_level leaves LOW), and the two screens reported
          -- different totals for the same set: 48,359 here against 48,687
          -- there, the 328 works sitting exactly on 40.
          COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS anomaly_count
        FROM projects
        {where}
        """,
        params,
        one=True,
    )
    money = query(
        f"""
        SELECT COALESCE(SUM(expenditure_amount), 0) AS vendor_payments,
               COUNT(*) AS payment_count
        FROM expenditures {where}
        """,
        params,
        one=True,
    )
    mps_row = query(
        f"""
        SELECT COALESCE(SUM(allocated_amount), 0) AS allocated_total,
               COUNT(DISTINCT mp_id) AS mp_count
        FROM mps {where}
        """,
        params,
        one=True,
    )
    return {**row, **money, **mps_row, "ls_term": ls_term}


@app.get("/api/projects")
def list_projects(
    q: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    risk_level: Optional[str] = None,
    ls_term: Optional[int] = Query(None, ge=17, le=18),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    filters, params = [], []
    if q:
        filters.append(
            "(work_name ILIKE %s OR mp_name ILIKE %s OR district ILIKE %s "
            "OR state ILIKE %s OR implementing_agency ILIKE %s)"
        )
        pattern = f"%{q}%"
        params += [pattern] * 5
    if state:
        filters.append("state = %s")
        params.append(state)
    if district:
        filters.append("district = %s")
        params.append(district)
    if risk_level:
        filters.append("risk_level = %s")
        params.append(risk_level)
    if ls_term:
        filters.append("ls_term = %s")
        params.append(ls_term)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    params += [limit, offset]

    return query(
        f"""
        SELECT id, work_name, ls_term, state, district, category, sector,
               implementing_agency, sanctioned_amount, overall_risk_score, risk_level
        FROM projects
        {where}
        ORDER BY overall_risk_score DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        params,
    )


@app.get("/api/filters")
def filters():
    # Small, cacheable payload for the projects-page dropdowns: states with
    # counts, and whichever risk levels actually appear. Districts (773) and
    # agencies (776) are intentionally left out — see /api/districts, which
    # a district dropdown could filter client-side by state if one is added.
    states = query(
        "SELECT state, COUNT(*) AS count FROM projects GROUP BY state ORDER BY state"
    )
    risk_levels = query(
        "SELECT DISTINCT risk_level FROM projects WHERE risk_level IS NOT NULL ORDER BY risk_level"
    )
    return {"states": states, "risk_levels": [r["risk_level"] for r in risk_levels]}


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


# An average over one work is not an average. Below this an agency's mean risk
# is whatever its single work scored, which put agencies holding one work at the
# top of the ranking ahead of agencies holding a thousand.
AGENCY_MIN_WORKS = 10


@app.get("/api/agencies")
def agencies(
    ls_term: Optional[int] = Query(None, ge=17, le=18),
    min_works: int = Query(AGENCY_MIN_WORKS, ge=1),
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """One row per agency per Lok Sabha term, ranked by average risk.

    An agency's vendor mix in one term says nothing about its mix in the other,
    so the two are not pooled.
    """
    params = []
    where = ""
    if ls_term:
        where = "WHERE ls_term = %s"
        params = [ls_term, ls_term]
    return query(
        f"""
        WITH work_stats AS (
            SELECT implementing_agency, ls_term,
                   COUNT(*) AS total_projects,
                   COUNT(*) FILTER (WHERE delay_days > 60) AS delayed_count,
                   COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS anomaly_count,
                   COALESCE(AVG(overall_risk_score), 0) AS avg_risk_score
            FROM projects {where} GROUP BY implementing_agency, ls_term
        ),
        vendor_stats AS (
            SELECT * FROM agency_vendor_profile {where}
        )
        SELECT w.implementing_agency, w.ls_term, w.total_projects, w.delayed_count,
               w.anomaly_count, w.avg_risk_score,
               v.vendor_count, v.transaction_count, v.total_spend,
               v.top_vendor, v.top_vendor_share_pct,
               COALESCE(v.concentration_risk, 0) AS concentration_risk
        -- LEFT: an agency with no expenditure rows keeps its works and simply
        -- has no vendor data, rather than dropping off the screen.
        FROM work_stats w
        LEFT JOIN vendor_stats v USING (implementing_agency, ls_term)
        WHERE w.total_projects >= %s
        ORDER BY w.avg_risk_score DESC, w.total_projects DESC
        LIMIT %s OFFSET %s
        """,
        params + [min_works, limit, offset],
    )


@app.get("/api/mps")
def mps(limit: int = Query(100, le=1000)):
    """MPs by the value of allocation they have never committed to a work.

    Every figure here is the source's own published per-MP aggregate rather
    than anything recomputed, so each can be checked against
    empoweredindian.in for the same MP.

    Two different balances, easy to confuse and reported separately:
      - idle_amount = allocated_amount - amount_recommended. Money that has
        never been committed to any work.
      - unspent_amount, which the source now calls "Balance Not Yet Paid to
        Vendors" - money committed to works and awaiting payment. It equals
        amount_recommended - total_expenditure on every one of the 1,548 rows.

    Sorted by idle amount rather than by utilisation: the lowest utilisation
    figures belong to Rajya Sabha members sworn in during 2025-26 who have had
    no time to spend anything, and ranking them as the worst would be wrong.
    """
    return query(
        """
        WITH work_stats AS (
            SELECT mp_id, ls_term,
                   COUNT(*) AS total_projects,
                   COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_works
            FROM projects WHERE mp_id IS NOT NULL GROUP BY mp_id, ls_term
        )
        SELECT m.mp_id, m.ls_term, m.mp_name, m.constituency, m.state, m.house,
               m.allocated_amount, m.amount_recommended, m.total_expenditure,
               m.utilization_pct, m.unspent_amount, m.completion_rate_pct,
               m.pending_payments,
               m.allocated_amount - m.amount_recommended AS idle_amount,
               COALESCE(w.total_projects, 0) AS total_projects,
               COALESCE(w.high_risk_works, 0) AS high_risk_works
        FROM mps m
        LEFT JOIN work_stats w USING (mp_id, ls_term)
        WHERE COALESCE(m.allocated_amount, 0) > 0
        ORDER BY (m.allocated_amount - m.amount_recommended) DESC NULLS LAST
        LIMIT %s
        """,
        [limit],
    )


@app.get("/api/data-freshness")
def data_freshness():
    """Latest successful load+score run, for the UI's freshness indicator.
    See data_refresh in data/schema.sql / task-12-refresh-report.md."""
    row = query(
        """
        SELECT finished_at, rows_loaded, rows_scored, rows_rejected, source
        FROM data_refresh
        WHERE status = 'success'
        ORDER BY finished_at DESC NULLS LAST
        LIMIT 1
        """,
        one=True,
    )
    return row or {}


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


# ---------------------------------------------------------------- alert queue

REVIEW_STATUSES = ("verified", "dismissed", "escalated")

# Everything the queue needs to justify one row on screen. Deliberately wide:
# a reviewer deciding whether a work is worth a site visit should not have to
# open a second page to see why it was flagged, and 50 rows of this is a few
# hundred KB.
_ALERT_COLUMNS = """
    p.id, p.work_key, p.work_name, p.description, p.ls_term, p.state, p.district,
    p.sector, p.category, p.implementing_agency, p.mp_name, p.constituency,
    p.sanctioned_amount, p.expenditure, p.work_status, p.delay_days,
    p.cost_deviation_pct, p.peer_median_cost, p.peer_count,
    p.max_similarity_score, p.similar_work_id,
    p.cost_risk, p.delay_risk, p.duplicate_risk, p.agency_risk, p.compliance_risk,
    p.overall_risk_score, p.risk_level, p.flagged_reasons,
    COALESCE(r.status, 'pending') AS review_status,
    r.note AS review_note, r.reviewer AS review_reviewer,
    r.updated_at AS review_updated_at
"""


def _alert_filters(q, state, district, sector, risk_level, ls_term, status, min_score):
    """Shared WHERE builder so the list and its total count can never drift."""
    filters, params = [], []
    if q:
        filters.append(
            "(p.work_name ILIKE %s OR p.description ILIKE %s OR p.mp_name ILIKE %s "
            "OR p.district ILIKE %s OR p.state ILIKE %s OR p.implementing_agency ILIKE %s)"
        )
        params += [f"%{q}%"] * 6
    for column, value in (
        ("p.state", state),
        ("p.district", district),
        ("p.sector", sector),
        ("p.risk_level", risk_level),
        ("p.ls_term", ls_term),
    ):
        if value is not None:
            filters.append(f"{column} = %s")
            params.append(value)
    if status == "pending":
        # No row in work_reviews is what 'pending' means - the table holds
        # decisions, not a placeholder for every one of 127k works.
        filters.append("r.status IS NULL")
    elif status:
        filters.append("r.status = %s")
        params.append(status)
    if min_score is not None:
        filters.append("p.overall_risk_score >= %s")
        params.append(min_score)
    return (f"WHERE {' AND '.join(filters)}" if filters else ""), params


@app.get("/api/alerts")
def alerts(
    q: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    sector: Optional[str] = None,
    risk_level: Optional[str] = None,
    ls_term: Optional[int] = Query(None, ge=17, le=18),
    status: Optional[str] = Query(None, pattern="^(pending|verified|dismissed|escalated)$"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """The triage queue: works ranked by risk, carrying their evidence and
    whatever a reviewer has already concluded about them."""
    where, params = _alert_filters(
        q, state, district, sector, risk_level, ls_term, status, min_score
    )
    rows = query(
        f"""
        SELECT {_ALERT_COLUMNS}
        FROM projects p
        LEFT JOIN work_reviews r ON r.work_key = p.work_key
        {where}
        ORDER BY p.overall_risk_score DESC NULLS LAST, p.id
        LIMIT %s OFFSET %s
        """,
        params + [limit, offset],
    )
    total = query(
        f"""
        SELECT COUNT(*) AS total
        FROM projects p
        LEFT JOIN work_reviews r ON r.work_key = p.work_key
        {where}
        """,
        params,
        one=True,
    )
    return {"total": total["total"], "limit": limit, "offset": offset, "alerts": rows}


@app.get("/api/alerts/summary")
def alerts_summary(min_score: float = Query(40, ge=0, le=100)):
    """Counts for the queue header. min_score defaults to 40 because that is
    where risk_level leaves LOW (see RISK_LEVEL_THRESHOLDS in data/scoring.py) -
    below it there is nothing to triage."""
    return query(
        """
        SELECT
          COUNT(*) AS in_scope,
          COUNT(*) FILTER (WHERE r.status IS NULL)          AS pending,
          COUNT(*) FILTER (WHERE r.status = 'escalated')    AS escalated,
          COUNT(*) FILTER (WHERE r.status = 'verified')     AS verified,
          COUNT(*) FILTER (WHERE r.status = 'dismissed')    AS dismissed,
          COUNT(*) FILTER (WHERE p.risk_level = 'HIGH')     AS high,
          COUNT(*) FILTER (WHERE p.risk_level = 'MEDIUM')   AS medium,
          COALESCE(SUM(p.sanctioned_amount) FILTER (WHERE r.status IS NULL), 0)
            AS pending_sanctioned_amount
        FROM projects p
        LEFT JOIN work_reviews r ON r.work_key = p.work_key
        WHERE p.overall_risk_score >= %s
        """,
        [min_score],
        one=True,
    )


class ReviewIn(BaseModel):
    work_key: str = Field(min_length=1, max_length=400)
    status: str
    note: Optional[str] = Field(default=None, max_length=2000)
    reviewer: Optional[str] = Field(default=None, max_length=120)


@app.post("/api/alerts/review")
def set_review(body: ReviewIn, x_review_token: Optional[str] = Header(default=None)):
    """Record a reviewer's decision about one work.

    The only write endpoint in the API, so it carries the only auth: a shared
    token in REVIEW_TOKEN. Fails closed - with the variable unset nobody can
    write, rather than everybody. That is deliberate: this deployment is public
    and unauthenticated otherwise, and a queue anyone can silently clear is
    worse than a read-only one.
    """
    expected = os.environ.get("REVIEW_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Reviews are disabled: REVIEW_TOKEN is not configured on the server.",
        )
    if x_review_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Review-Token.")
    if body.status not in REVIEW_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"status must be one of {', '.join(REVIEW_STATUSES)}"
        )
    exists = query(
        "SELECT 1 FROM projects WHERE work_key = %s LIMIT 1", [body.work_key], one=True
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="No work with that work_key.")
    # One statement, so the trail and the current verdict cannot diverge. A
    # second call in the same transaction would do, but this needs no new
    # database helper and is atomic by construction.
    return execute(
        """
        WITH recorded AS (
            INSERT INTO work_review_events (work_key, status, note, reviewer)
            VALUES (%s, %s, %s, %s)
            RETURNING work_key, status, note, reviewer, created_at
        )
        INSERT INTO work_reviews (work_key, status, note, reviewer, updated_at)
        SELECT work_key, status, note, reviewer, created_at FROM recorded
        ON CONFLICT (work_key) DO UPDATE
          SET status = EXCLUDED.status,
              note = EXCLUDED.note,
              reviewer = EXCLUDED.reviewer,
              updated_at = EXCLUDED.updated_at
        RETURNING work_key, status, note, reviewer, updated_at
        """,
        [body.work_key, body.status, body.note, body.reviewer],
        returning=True,
    )


@app.get("/api/alerts/history")
def review_history(work_key: str = Query(min_length=1, max_length=400)):
    """Every decision ever recorded against one work, newest first.

    work_key carries '|', '(' and spaces, so it travels as a query parameter
    rather than a path segment.
    """
    return {
        "work_key": work_key,
        "events": query(
            """
            SELECT status, note, reviewer, created_at
            FROM work_review_events
            WHERE work_key = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            [work_key],
        ),
    }


# ------------------------------------------------------------ cohort signals

# Kept beside the codes in data/detectors.py. The interface has to be able to
# say what a detector does and, more importantly, what it does not prove -
# a finding with no stated limit is the thing that gets a system laughed out of
# a hearing.
DETECTORS = {
    "D-01": {
        "name": "Year-end payment burst",
        "subject": "agency",
        "what": "Share of an agency's fiscal-year payments falling in March, the month the Indian financial year closes and unspent money can lapse.",
        "limit": "An agency whose sanctions all arrive in the last quarter looks identical. This is a spending pattern, not a finding.",
    },
    "D-02": {
        "name": "First-digit anomaly",
        "subject": "agency",
        "what": "Departure of an agency's payment amounts from Benford's first-digit law, measured as mean absolute deviation.",
        "limit": "The whole population fails the textbook test — the median agency scores 6.2 where Nigrini calls 1.5 nonconformant — because MPLADS amounts are capped, rounded and repeated by design. This ranks agencies against each other, not against the law. It is the weakest signal here and is never evidence on its own.",
    },
    "D-03": {
        "name": "Idle allocation",
        "subject": "mp",
        "what": "Allocation an MP has never committed to any work — what the portal publishes as allocated, less what it publishes as recommended.",
        "limit": "Not a suspicion. MPLADS funds stay spendable after a term ends, and the median MP-term leaves 16.5% uncommitted, so only well above that appears here. It is deliberately not the source's \"Balance Not Yet Paid to Vendors\", which is money already committed to works and merely awaiting payment.",
    },
    "D-04": {
        "name": "Uniform sanction amount",
        "subject": "agency",
        "what": "Share of an agency's works sanctioned at one single identical amount.",
        "limit": "Round figures are normal and similar works legitimately cost the same. One figure covering nearly every work is what this looks for, and it means the costing is worth seeing, not that it is wrong.",
    },
}


@app.get("/api/detectors")
def detectors_catalogue():
    """What each detector measures and what it does not claim, with how many
    findings it currently holds."""
    counts = {
        r["code"]: r
        for r in query(
            """
            SELECT code, COUNT(*) AS findings, MAX(severity) AS max_severity
            FROM detector_findings GROUP BY code
            """
        )
    }
    return [
        {
            "code": code,
            **meta,
            "findings": int(counts.get(code, {}).get("findings", 0)),
            "max_severity": float(counts[code]["max_severity"]) if code in counts else None,
        }
        for code, meta in sorted(DETECTORS.items())
    ]


@app.get("/api/detectors/findings")
def detector_findings(
    code: Optional[str] = None,
    subject_type: Optional[str] = Query(None, pattern="^(agency|mp)$"),
    ls_term: Optional[int] = Query(None, ge=17, le=18),
    q: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    filters, params = [], []
    if code:
        filters.append("code = %s")
        params.append(code)
    if subject_type:
        filters.append("subject_type = %s")
        params.append(subject_type)
    if ls_term:
        filters.append("ls_term = %s")
        params.append(ls_term)
    if q:
        filters.append("(subject ILIKE %s OR headline ILIKE %s)")
        params += [f"%{q}%"] * 2
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = query(
        f"""
        SELECT code, subject_type, subject, ls_term, period, severity, headline, evidence
        FROM detector_findings {where}
        ORDER BY severity DESC, code, subject
        LIMIT %s OFFSET %s
        """,
        params + [limit, offset],
    )
    total = query(
        f"SELECT COUNT(*) AS total FROM detector_findings {where}", params, one=True
    )
    return {"total": total["total"], "limit": limit, "offset": offset, "findings": rows}


# ------------------------------------------------------------------- states

# The source's own bands, from its states page: >=80% is a high performer,
# 50-79% average, below 50% needs improvement. Kept identical so the two
# screens sort a state into the same bucket.
STATE_BANDS = {"high": 80.0, "average": 50.0}


@app.get("/api/states")
def states(ls_term: int = Query(18, ge=17, le=18)):
    """Per-state totals, plus what our scoring adds on top.

    Every money figure comes from the source's own per-MP aggregates rather
    than being recomputed from works, which is what lets a reader check any row
    against empoweredindian.in. Verified 2026-09-09 against
    api.empoweredindian.in/api/summary/states: all 36 states match on
    allocation, expenditure, amount recommended, MP count and completed works.

    Two rates, because the source publishes one number under both names. Its
    API returns utilizationPercentage identical to expenditurePercentage, with
    the field `utilizationDefinition: "vendor_expenditure_legacy"` marking the
    conflation, while its overview page calls something else "Fund
    Utilization". They are different questions and both are reported here:

      - paid_rate: expenditure / allocated. Money actually out the door. This
        is the figure the source's state cards show.
      - committed_rate: recommended / allocated. Money attached to a work,
        whether or not it has been paid.
    """
    return query(
        """
        WITH money AS (
            SELECT state,
                   SUM(allocated_amount) AS allocated,
                   SUM(amount_recommended) AS recommended,
                   SUM(total_expenditure) AS expenditure,
                   COUNT(DISTINCT mp_id) AS mp_count,
                   SUM(completed_works) AS completed_works,
                   SUM(recommended_works) AS recommended_works
            FROM mps WHERE ls_term = %s AND state IS NOT NULL
            GROUP BY state
        ),
        risk AS (
            SELECT state,
                   COUNT(*) AS works,
                   COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
                   COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue,
                   COALESCE(SUM(sanctioned_amount) FILTER (WHERE overall_risk_score >= 40), 0)
                     AS flagged_amount,
                   AVG(overall_risk_score) AS avg_risk
            FROM projects WHERE ls_term = %s GROUP BY state
        )
        SELECT m.state, m.allocated, m.recommended, m.expenditure, m.mp_count,
               m.completed_works, m.recommended_works,
               CASE WHEN m.allocated > 0
                    THEN ROUND(m.expenditure / m.allocated * 100, 1) END AS paid_rate,
               CASE WHEN m.allocated > 0
                    THEN ROUND(m.recommended / m.allocated * 100, 1) END AS committed_rate,
               CASE WHEN m.recommended_works > 0
                    THEN ROUND(m.completed_works::numeric / m.recommended_works * 100, 1)
                    END AS completion_rate,
               COALESCE(r.works, 0) AS works,
               COALESCE(r.high_risk, 0) AS high_risk,
               COALESCE(r.in_queue, 0) AS in_queue,
               COALESCE(r.flagged_amount, 0) AS flagged_amount,
               ROUND(r.avg_risk, 1) AS avg_risk
        FROM money m
        LEFT JOIN risk r USING (state)
        ORDER BY m.expenditure / NULLIF(m.allocated, 0) DESC NULLS LAST
        """,
        [ls_term, ls_term],
    )
