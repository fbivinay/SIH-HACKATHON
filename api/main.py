import json
import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from db import execute, query

app = FastAPI(title="Kasauti API")
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
        FROM projects_scored
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

    rows = query(
        f"""
        SELECT id, work_key, work_name, ls_term, state, district, category, sector,
               implementing_agency, sanctioned_amount, overall_risk_score, risk_level
        FROM projects_scored
        {where}
        ORDER BY overall_risk_score DESC NULLS LAST, id
        LIMIT %s OFFSET %s
        """,
        params,
    )
    # The register paginates like the queue does, and a page cannot show
    # "1-50 of N" without N.
    total = query(
        f"SELECT COUNT(*) AS total FROM projects_scored {where}", params[:-2], one=True
    )
    return {"total": total["total"], "limit": limit, "offset": offset, "projects": rows}


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
        "SELECT DISTINCT risk_level FROM project_scores WHERE risk_level IS NOT NULL ORDER BY risk_level"
    )
    return {"states": states, "risk_levels": [r["risk_level"] for r in risk_levels]}


@app.get("/api/projects/by-key")
def project_by_key(work_key: str = Query(min_length=1, max_length=400)):
    """Look a work up by the identifier that survives a refresh.

    `id` is a serial the loader reassigns every night, so a link to
    /api/projects/12524 points at a different work tomorrow. work_key does not
    move, which is what makes a shared or bookmarked link durable.
    """
    row = query("SELECT * FROM projects_scored WHERE work_key = %s", [work_key], one=True)
    if row is None:
        raise HTTPException(status_code=404, detail="No work with that work_key")
    return row


@app.get("/api/projects/{project_id}")
def project_detail(project_id: int):
    row = query("SELECT * FROM projects_scored WHERE id = %s", [project_id], one=True)
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


@app.get("/api/map/states")
def map_states():
    """Per-state figures for the choropleth.

    flagged_share is what the map colours by. Average score cannot: every one
    of the 36 states averages between 6.5 and 37.2, so all 36 fall in the LOW
    band and a band-coloured map is a uniform green sheet that says nothing.
    The share of a state's works above the review threshold runs 0% to 43.1% -
    real variation, and the actionable quantity, since it is the proportion of
    that state's works somebody has to go and look at.
    """
    return query(
        """
        SELECT state,
               COUNT(*) AS total_projects,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS flagged_count,
               COALESCE(AVG(overall_risk_score), 0) AS avg_risk_score,
               ROUND(100.0 * COUNT(*) FILTER (WHERE overall_risk_score >= 40)
                     / NULLIF(COUNT(*), 0), 1) AS flagged_share
        FROM projects_scored GROUP BY state
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
            FROM projects_scored {where} GROUP BY implementing_agency, ls_term
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
            FROM projects_scored WHERE mp_id IS NOT NULL GROUP BY mp_id, ls_term
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
        FROM projects_scored GROUP BY state, district
        ORDER BY avg_risk_score DESC
        """
    )


# ---------------------------------------------------------------- alert queue

# The compliance component's share of the overall score, from RISK_WEIGHTS in
# data/scoring.py.
RISK_WEIGHTS_COMPLIANCE_PCT = 15

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
        FROM projects_scored p
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
        FROM projects_scored p
        LEFT JOIN work_reviews r ON r.work_key = p.work_key
        {where}
        """,
        params,
        one=True,
    )
    return {"total": total["total"], "limit": limit, "offset": offset, "alerts": rows}


@app.get("/api/alerts/summary")
def alerts_summary(
    q: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    sector: Optional[str] = None,
    risk_level: Optional[str] = None,
    ls_term: Optional[int] = Query(None, ge=17, le=18),
    status: Optional[str] = None,
    min_score: float = Query(40, ge=0, le=100),
):
    """Counts for the queue header. min_score defaults to 40 because that is
    where risk_level leaves LOW (see RISK_LEVEL_THRESHOLDS in data/scoring.py) -
    below it there is nothing to triage.

    Takes the same filters as /api/alerts and builds its WHERE with the same
    helper, so the tiles describe the queue underneath them. They used to take
    only min_score: filter the table to one district and the header still
    reported the whole country, which reads as "47,719 awaiting review in
    Kozhikode".
    """
    where, params = _alert_filters(
        q, state, district, sector, risk_level, ls_term, status, min_score
    )
    return query(
        f"""
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
        FROM projects_scored p
        LEFT JOIN work_reviews r ON r.work_key = p.work_key
        {where}
        """,
        params,
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
            FROM projects_scored WHERE ls_term = %s GROUP BY state
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


# ---------------------------------------------------------------- rule book

# The compliance component's rules, each with the exact predicate scoring
# applies, so a reader can check the claim rather than take it.
#
# `basis` says where a rule comes from. Deliberately no clause numbers: the
# MPLADS guidelines are not in this repository and inventing "clause 3.12.1"
# to look authoritative is the same failure as inventing a beneficiary count.
COMPLIANCE_RULES = [
    {
        "code": "C-01",
        "name": "Spending beyond the sanction",
        "weight": 60,
        "predicate": "expenditure > sanctioned_amount",
        "checks": "A work that has cost more than the amount sanctioned for it.",
        "basis": "The scheme sanctions a specific amount per work; spending past it needs a revised sanction.",
        "reason": "Expenditure exceeds sanctioned amount",
    },
    {
        "code": "C-02",
        "name": "Recommended work with no schedule",
        "weight": 20,
        "predicate": "work_status = 'recommended' AND (start_date IS NULL OR expected_completion IS NULL)",
        "checks": "A work put forward without the dates that would let anyone tell whether it is late.",
        "basis": "A recommendation carries a date; without an expected completion no delay can be computed.",
        "reason": "Missing start or expected completion date",
    },
    {
        "code": "C-03",
        "name": "Completed with no completion date",
        "weight": 20,
        "predicate": "work_status = 'completed' AND actual_completion IS NULL",
        "checks": "A work marked finished with nothing on record saying when.",
        "basis": "Completion is the event that closes a work; the date is what makes it auditable.",
        "reason": "Marked completed with no actual completion date",
    },
    {
        "code": "C-04",
        "name": "Completed with no photograph",
        "weight": 30,
        "predicate": "work_status = 'completed' AND has_images IS FALSE",
        "checks": "A finished work with no photographic record that it exists.",
        "basis": "The portal carries a photograph flag per work; a completed asset with none has no visual evidence behind it.",
        "reason": "Completed work has no photographic documentation on record",
    },
]

# Checks the published data cannot answer at all. Stated because a rule book
# listing only what passes is the more misleading half.
COMPLIANCE_BLIND_SPOTS = [
    {
        "name": "Whether a work overspent its sanction",
        "why": "The source publishes one figure per completed work - the final amount - which the loader records as both the sanction and the expenditure. The two can never differ, so C-01 cannot fire on this data. It is kept because a source that later publishes them separately would make it live.",
    },
    {
        "name": "Whether a work is a permissible category",
        "why": "MPLADS restricts what funds may be spent on, but the portal's own category column reads 'Normal/Others' on 98.1% of works. The sector this system shows is derived from the description text, which is good enough to compare like with like and not good enough to rule a work impermissible. The twelve sectors are also not exhaustive: roughly 1,750 works are electrical - substations, transformers, 11kV lines - and have no sector of their own, so they sit wherever their description reads closest.",
    },
    {
        "name": "Whether the money bought what was claimed",
        "why": "No progress percentage, beneficiary count, geo-tag, bill value or site photograph is published. Nothing here can speak to physical quality or existence - that is what sending someone to look is for, which is what the queue is.",
    },
    {
        "name": "Whether the sanction ceiling per work was respected",
        "why": "Ceilings vary by work type and year and are not published alongside the works. Cost is therefore judged against comparable works in the same district and sector, not against a rule.",
    },
]


@app.get("/api/compliance")
def compliance():
    """The rule book, with how many works each rule currently catches.

    A rule finding nothing means one of two very different things, and the
    status says which: `clear` is the data satisfying the rule, `inert` is the
    rule being unable to fire at all.
    """
    rows = []
    for rule in COMPLIANCE_RULES:
        hit = query(
            "SELECT COUNT(*) AS n FROM project_scores WHERE flagged_reasons @> %s::jsonb",
            [json.dumps([rule["reason"]])],
            one=True,
        )
        breaches = int(hit["n"])
        satisfiable = query(
            f"SELECT COUNT(*) AS n FROM projects WHERE {rule['predicate']}", one=True
        )
        possible = int(satisfiable["n"])
        rows.append({
            **rule,
            "breaches": breaches,
            "status": "breached" if breaches else ("clear" if possible == 0 and rule["code"] != "C-01" else "inert"),
        })
    scored = query("SELECT COUNT(*) AS n FROM project_scores", one=True)
    breaching = query(
        "SELECT COUNT(*) AS n FROM project_scores WHERE compliance_risk > 0", one=True
    )
    return {
        "rules": rows,
        "blind_spots": COMPLIANCE_BLIND_SPOTS,
        "works_scored": int(scored["n"]),
        "works_breaching": int(breaching["n"]),
        "weight_in_score": int(RISK_WEIGHTS_COMPLIANCE_PCT),
    }


# ------------------------------------------------------------------ provenance


# What the designated dataset exposes without an account, enumerated from the
# portal's own JavaScript (endpoint strings are stored reversed and
# unicode-escaped) and then called directly. Measured 2026-09-10.
#
# "Why not the source you were given" is the first question this project should
# expect, and it deserves an answer made of evidence. The short version: the
# portal does publish works, but only one narrow slice at a time, behind an SMS
# one-time password, under an explicit rate limit. There is no bulk export.
OFFICIAL_INTERFACE = {
    "url": "https://mplads.mospi.gov.in/digigov/dashboard.html",
    "checked_on": "2026-09-10",
    "endpoints": [
        {"endpoint": "POST /rest/PreLoginDashboardData/getTilesData",
         "returns": "Six headline totals for one tenure and house - allocated, expenditure, works recommended, sanctioned, completed, calamity.",
         "access": "open"},
        {"endpoint": "POST /rest/PreLoginDashboardData/getTenureData",
         "returns": "The two tenures on record: 17th and 18th Lok Sabha.", "access": "open"},
        {"endpoint": "POST /rest/PreLoginDashboardData/getStateData",
         "returns": "36 state names and ids.", "access": "open"},
        {"endpoint": "POST /rest/PreLoginCitizenWorkRcmdRest/getDistrictByState",
         "returns": "Districts in a state.", "access": "open"},
        {"endpoint": "POST /rest/PreLoginCitizenWorkRcmdRest/getMpByDistrictAndState",
         "returns": "Members for a district and tenure.", "access": "open"},
        {"endpoint": "POST /rest/PreLoginCitizenWorkRcmdRest/getVillageByBlock",
         "returns": "Villages, blocks, cities and wards - the address hierarchy.", "access": "open"},
        {"endpoint": "POST /rest/PreLoginCitizenWorkRcmdRest/generateOTPForCitizenLogin",
         "returns": "Sends a one-time password to an Indian mobile number, behind a captcha.",
         "access": "otp"},
        {"endpoint": "POST /rest/PreLoginCitizenWorkRcmdRest/getAllCompletedWorkByMP",
         "returns": "Completed works - the only work-level data published. Requires a verified mobile number and OTP in the request body, and returns one member's completed works in one ward at a time, so a citizen can rate them.",
         "access": "otp"},
        {"endpoint": "POST /rest/PreLoginDashboardData/getRedirectUrl",
         "returns": "An empty string; the way through to the authenticated portal.",
         "access": "login"},
    ],
    "verdict": "The portal publishes works, but only completed ones, only for one member in one ward at a time, only after an SMS one-time password, and under a rate limit its own code apologises for. This system reads 250,839 works - recommended as well as completed - and 272,263 payments with vendor names, which no open endpoint serves in any quantity. Empowered Indian republishes exactly that record as machine-readable exports, which is why it is the loader's source, and why every headline figure above is reconciled nightly against the official endpoints rather than taken on trust.",
    "login_wall": "Every path under /digigov/ other than the dashboard answers 302 to /digigov/Login.zul.",
}


@app.get("/api/provenance")
def provenance():
    """How our figures compare with the official MoSPI dashboard.

    The problem statement designates mplads.mospi.gov.in as the dataset. We
    load from Empowered Indian, which aggregates it - a claim worth checking
    rather than asserting, so scripts/verify_mospi.py checks it against the
    portal's own pre-login endpoints and records the result here.
    """
    rows = query(
        """
        SELECT metric, ours, official, unit, gap_pct, note, checked_at,
               aggregator, aggregator_gap_pct
        FROM source_reconciliation ORDER BY metric
        """
    )
    freshness = query(
        """
        SELECT finished_at, rows_loaded, rows_scored, source
        FROM data_refresh WHERE status = 'success'
        ORDER BY finished_at DESC NULLS LAST LIMIT 1
        """,
        one=True,
    )
    # Why our own hop is not zero, counted rather than asserted. The page used
    # to state these as three typed-in numbers measured once off a CSV; they
    # drifted the moment the extract changed, which is the same failure the
    # deck had before its figures were read from here.
    rejects = query(
        """WITH dated AS (
               SELECT reason,
                      SUBSTRING(source_file FROM '\\d{4}-\\d{2}-\\d{2}') AS extract_date
               FROM rejected_rows
           )
           SELECT reason, COUNT(*) AS rows
           FROM dated
           WHERE extract_date = (SELECT MAX(extract_date) FROM dated)
           GROUP BY reason ORDER BY rows DESC"""
    )
    worst = max((abs(float(r["gap_pct"])) for r in rows if r["gap_pct"] is not None),
                default=None)
    # The chain has two hops. Ours-to-aggregator is the one this system is
    # responsible for; aggregator-to-MoSPI is upstream lag we can measure but
    # not fix. Reporting a single number invites reading the whole gap as ours.
    our_hop = max(
        (abs(float(r["ours"]) - float(r["aggregator"])) / float(r["aggregator"]) * 100
         for r in rows
         if r["aggregator"] not in (None, 0) and r["ours"] is not None),
        default=None,
    )
    upstream_hop = max(
        (abs(float(r["aggregator_gap_pct"])) for r in rows
         if r["aggregator_gap_pct"] is not None),
        default=None,
    )
    return {
        "rows": rows,
        "worst_gap_pct": worst,
        "worst_our_hop_pct": our_hop,
        "worst_upstream_hop_pct": upstream_hop,
        "last_refresh": freshness or {},
        "official_interface": OFFICIAL_INTERFACE,
        "rejects": rejects,
        "chain": [
            {
                "step": "Ministry of Statistics and Programme Implementation",
                "what": "Publishes the MPLADS record at mplads.mospi.gov.in, the dataset this problem statement designates.",
            },
            {
                "step": "Empowered Indian",
                "what": "Aggregates that portal and publishes machine-readable exports of the works, payments and per-MP figures the official site shows only as a dashboard.",
            },
            {
                "step": "This system",
                "what": "Loads those exports nightly, scores every work against its peers, and records the comparison above so the chain can be audited rather than trusted.",
            },
        ],
    }


# ---------------------------------------------------------------------- trends

# An agency with a handful of open works and no recent payment is ordinary. One
# holding twenty or more, silent for half a year, is worth a phone call.
QUIET_MIN_OPEN_WORKS = 20
QUIET_DAYS = 180


@app.get("/api/trends")
def trends(state: Optional[str] = None):
    """Payments over time, by month and by fiscal year, plus what has gone quiet.

    The brief asks for trend analysis and early warning. Both are read from
    expenditure_date across 272,263 payments spanning 39 months - the only
    genuinely temporal thing the published record contains.
    """
    where, params = ("WHERE state = %s", [state]) if state else ("", [])

    monthly = query(
        f"""
        SELECT to_char(date_trunc('month', expenditure_date), 'YYYY-MM') AS month,
               COUNT(*) AS payments,
               COALESCE(SUM(expenditure_amount), 0) AS amount
        FROM expenditures
        {where or "WHERE TRUE"} AND expenditure_date IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """,
        params,
    )

    # India's fiscal year runs April to March, which is the whole point: the
    # year-end share is the number that says whether money is being spent as
    # work happens or shovelled out before it lapses.
    fiscal = query(
        f"""
        SELECT CASE WHEN EXTRACT(MONTH FROM expenditure_date) >= 4
                    THEN EXTRACT(YEAR FROM expenditure_date)
                    ELSE EXTRACT(YEAR FROM expenditure_date) - 1 END::int AS fy,
               COUNT(*) AS payments,
               COALESCE(SUM(expenditure_amount), 0) AS amount,
               ROUND(100.0 * COUNT(*) FILTER (WHERE EXTRACT(MONTH FROM expenditure_date) = 3)
                     / NULLIF(COUNT(*), 0), 1) AS march_share,
               MIN(expenditure_date) AS first_payment,
               MAX(expenditure_date) AS last_payment
        FROM expenditures
        {where or "WHERE TRUE"} AND expenditure_date IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """,
        params,
    )

    # Bound parameters rather than %-formatting the finished string. The
    # f-string interpolates the state filter twice, each carrying its own
    # placeholder, so formatting the result left four placeholders against a
    # two-tuple and /api/trends?state=X raised TypeError before psycopg2 saw
    # it. Nothing here may carry a literal percent sign either - psycopg2
    # scans the whole string, SQL comments included.
    quiet = query(
        f"""
        WITH last_pay AS (
            SELECT implementing_agency, MAX(expenditure_date) AS last_paid,
                   COUNT(*) AS payments
            FROM expenditures {where} GROUP BY implementing_agency
        ),
        open_work AS (
            SELECT implementing_agency,
                   COUNT(*) FILTER (WHERE work_status = 'recommended') AS open_works,
                   COALESCE(SUM(sanctioned_amount) FILTER (WHERE work_status = 'recommended'), 0)
                     AS open_value
            FROM projects {where} GROUP BY implementing_agency
        )
        SELECT l.implementing_agency, l.last_paid, l.payments,
               o.open_works, o.open_value,
               (CURRENT_DATE - l.last_paid) AS days_silent
        FROM last_pay l JOIN open_work o USING (implementing_agency)
        WHERE l.last_paid < CURRENT_DATE - (%s || ' days')::interval
          AND o.open_works >= %s
        ORDER BY o.open_value DESC
        LIMIT 50
        """,
        params + params + [QUIET_DAYS, QUIET_MIN_OPEN_WORKS],
    )

    return {
        "monthly": monthly,
        "fiscal_years": fiscal,
        "quiet_agencies": quiet,
        "quiet_rule": {
            "days": QUIET_DAYS,
            "min_open_works": QUIET_MIN_OPEN_WORKS,
        },
        "state": state,
    }


# ------------------------------------------------------------------ one MP


@app.get("/api/mps/{mp_id}")
def mp_detail(mp_id: str, ls_term: Optional[int] = Query(None, ge=17, le=18)):
    """Everything on record for one Member of Parliament.

    The brief asks for decision-support dashboards for Members of Parliament
    first, and an MP's question is narrower than the national one: what did I
    recommend, what got built, what is still waiting, and which of it is being
    flagged. Money figures are the portal's own per-MP aggregates, so an MP can
    check this page against the Ministry's.
    """
    terms = query(
        """
        SELECT mp_id, ls_term, mp_name, constituency, state, house,
               allocated_amount, amount_recommended, total_expenditure,
               utilization_pct, completion_rate_pct, unspent_amount,
               allocated_amount - amount_recommended AS idle_amount,
               completed_works, recommended_works, pending_payments
        FROM mps WHERE mp_id = %s
        ORDER BY ls_term DESC
        """,
        [mp_id],
    )
    if not terms:
        raise HTTPException(status_code=404, detail="No MP with that id")

    where, params = ("AND ls_term = %s", [ls_term]) if ls_term else ("", [])
    works = query(
        f"""
        SELECT COUNT(*) AS works,
               COUNT(*) FILTER (WHERE work_status = 'completed') AS completed,
               COUNT(*) FILTER (WHERE work_status = 'recommended') AS pending,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned,
               COALESCE(SUM(sanctioned_amount) FILTER (WHERE overall_risk_score >= 40), 0)
                 AS flagged_value,
               COUNT(DISTINCT district) AS districts,
               COUNT(DISTINCT implementing_agency) AS agencies
        FROM projects_scored WHERE mp_id = %s {where}
        """,
        [mp_id] + params,
        one=True,
    )
    sectors = query(
        f"""
        SELECT COALESCE(sector, 'Other') AS sector, COUNT(*) AS works,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned
        FROM projects_scored WHERE mp_id = %s {where}
        GROUP BY 1 ORDER BY works DESC LIMIT 8
        """,
        [mp_id] + params,
    )
    top = query(
        f"""
        SELECT id, work_key, work_name, district, sanctioned_amount,
               overall_risk_score, risk_level, flagged_reasons
        FROM projects_scored
        WHERE mp_id = %s {where} AND overall_risk_score IS NOT NULL
        ORDER BY overall_risk_score DESC, id
        LIMIT 10
        """,
        [mp_id] + params,
    )
    findings = query(
        "SELECT code, headline, severity FROM detector_findings "
        "WHERE subject_type = 'mp' AND subject = %s ORDER BY severity DESC",
        [mp_id],
    )
    return {
        "terms": terms,
        "works": works,
        "sectors": sectors,
        "top_flagged": top,
        "findings": findings,
    }


# ------------------------------------------------- state and district desks
#
# The brief asks for decision-support dashboards for four audiences: Members of
# Parliament, State Nodal Authorities, District Authorities, and the Ministry.
# The Ministry's question is the national one every other screen answers, and
# an MP's is /api/mps/{mp_id}. These two are the middle of that chain, and the
# middle is where MPLADS actually gets implemented: a State Nodal Authority
# releases funds to districts and answers for the state's utilisation, a
# District Authority is the implementing agency's supervisor and answers for
# individual works.
#
# Both deliberately return one payload rather than making the page fan out to
# six endpoints: a district officer on a bad connection should pay one round
# trip, and a single query set cannot disagree with itself the way six can.


def _risk_rollup(where: str, params: list) -> dict:
    """Works-side totals for any scope. One query so scopes cannot drift."""
    return query(
        f"""
        SELECT COUNT(*) AS works,
               COUNT(*) FILTER (WHERE work_status = 'completed') AS completed,
               COUNT(*) FILTER (WHERE work_status = 'recommended') AS pending,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned,
               COALESCE(SUM(expenditure), 0) AS expenditure,
               COALESCE(SUM(sanctioned_amount) FILTER (WHERE overall_risk_score >= 40), 0)
                 AS flagged_amount,
               COUNT(DISTINCT district) AS districts,
               COUNT(DISTINCT implementing_agency) AS agencies,
               COUNT(DISTINCT mp_id) AS members,
               ROUND(AVG(overall_risk_score), 1) AS avg_risk
        FROM projects_scored {where}
        """,
        params,
        one=True,
    )


@app.get("/api/states/{state}")
def state_detail(state: str, ls_term: int = Query(18, ge=17, le=18)):
    """One state's desk: the State Nodal Authority's view.

    Money comes from the source's per-MP aggregates (same figures as
    /api/states, so this page and the state list can never disagree); the
    district table and everything below it comes from the works.
    """
    money = query(
        """
        SELECT SUM(allocated_amount) AS allocated,
               SUM(amount_recommended) AS recommended,
               SUM(total_expenditure) AS expenditure,
               COUNT(DISTINCT mp_id) AS mp_count,
               SUM(completed_works) AS completed_works,
               SUM(recommended_works) AS recommended_works
        FROM mps WHERE ls_term = %s AND state = %s
        """,
        [ls_term, state],
        one=True,
    )
    works = _risk_rollup("WHERE ls_term = %s AND state = %s", [ls_term, state])
    if not money["mp_count"] and not works["works"]:
        raise HTTPException(status_code=404, detail="No state by that name in this term")

    districts = query(
        """
        SELECT district,
               COUNT(*) AS works,
               COUNT(*) FILTER (WHERE work_status = 'completed') AS completed,
               COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned,
               COALESCE(SUM(sanctioned_amount) FILTER (WHERE overall_risk_score >= 40), 0)
                 AS flagged_amount,
               COUNT(DISTINCT implementing_agency) AS agencies,
               ROUND(AVG(overall_risk_score), 1) AS avg_risk
        FROM projects_scored
        WHERE ls_term = %s AND state = %s AND district IS NOT NULL
        GROUP BY district
        ORDER BY in_queue DESC, works DESC
        """,
        [ls_term, state],
    )
    members = query(
        """
        WITH w AS (
            SELECT mp_id, COUNT(*) AS works,
                   COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue
            FROM projects_scored WHERE ls_term = %s AND state = %s GROUP BY mp_id
        )
        SELECT m.mp_id, m.mp_name, m.constituency, m.house,
               m.allocated_amount, m.total_expenditure, m.utilization_pct,
               m.completion_rate_pct,
               -- The source's utilization_pct is the COMMITTED rate: measured
               -- across all 773 funded term-18 members it equals
               -- amount_recommended / allocated_amount, and equals
               -- total_expenditure / allocated_amount on only 41 of them. The
               -- desk ranks members by money actually out the door, so it has
               -- to compute that itself rather than reuse the source's field.
               CASE WHEN m.allocated_amount > 0
                    THEN ROUND(m.total_expenditure / m.allocated_amount * 100, 1)
                    END AS paid_pct,
               m.allocated_amount - m.amount_recommended AS idle_amount,
               COALESCE(w.works, 0) AS works, COALESCE(w.in_queue, 0) AS in_queue
        FROM mps m LEFT JOIN w USING (mp_id)
        WHERE m.ls_term = %s AND m.state = %s
        ORDER BY paid_pct ASC NULLS FIRST
        """,
        [ls_term, state, ls_term, state],
    )
    sectors = query(
        """
        SELECT COALESCE(sector, 'Other') AS sector, COUNT(*) AS works,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue
        FROM projects_scored WHERE ls_term = %s AND state = %s
        GROUP BY 1 ORDER BY works DESC LIMIT 10
        """,
        [ls_term, state],
    )
    top = query(
        """
        SELECT id, work_key, work_name, district, implementing_agency, mp_name,
               sanctioned_amount, overall_risk_score, risk_level, flagged_reasons
        FROM projects_scored
        WHERE ls_term = %s AND state = %s AND overall_risk_score IS NOT NULL
        ORDER BY overall_risk_score DESC, id
        LIMIT 10
        """,
        [ls_term, state],
    )
    findings = query(
        """
        WITH agencies AS (
            SELECT DISTINCT implementing_agency AS name
            FROM projects WHERE state = %s AND ls_term = %s
        ),
        members AS (SELECT mp_id FROM mps WHERE state = %s AND ls_term = %s)
        SELECT code, subject_type, subject, period, severity, headline
        FROM detector_findings f
        WHERE f.ls_term = %s
          AND ((f.subject_type = 'agency' AND f.subject IN (SELECT name FROM agencies))
            OR (f.subject_type = 'mp' AND f.subject IN (SELECT mp_id FROM members)))
        ORDER BY severity DESC, code
        LIMIT 25
        """,
        [state, ls_term, state, ls_term, ls_term],
    )
    return {
        "state": state,
        "ls_term": ls_term,
        "money": money,
        "works": works,
        "districts": districts,
        "members": members,
        "sectors": sectors,
        "top_flagged": top,
        "findings": findings,
    }


@app.get("/api/districts/{state}/{district}")
def district_detail(state: str, district: str, ls_term: int = Query(18, ge=17, le=18)):
    """One district's desk: the District Authority's view.

    A district officer supervises implementing agencies, so the agency table is
    the centre of this page rather than a footnote. There is no per-district
    money aggregate published anywhere - allocation is per MP, not per district
    - so every figure here is summed from the works themselves and labelled as
    sanctioned rather than allocated.
    """
    scope = "WHERE ls_term = %s AND state = %s AND district = %s"
    args = [ls_term, state, district]
    works = _risk_rollup(scope, args)
    if not works["works"]:
        raise HTTPException(status_code=404, detail="No works for that district in this term")

    agencies = query(
        """
        SELECT p.implementing_agency,
               COUNT(*) AS works,
               COUNT(*) FILTER (WHERE p.work_status = 'completed') AS completed,
               COUNT(*) FILTER (WHERE p.risk_level = 'HIGH') AS high_risk,
               COUNT(*) FILTER (WHERE p.overall_risk_score >= 40) AS in_queue,
               COALESCE(SUM(p.sanctioned_amount), 0) AS sanctioned,
               ROUND(AVG(p.overall_risk_score), 1) AS avg_risk,
               v.vendor_count, v.top_vendor, v.top_vendor_share_pct
        FROM projects_scored p
        LEFT JOIN agency_vendor_profile v
          ON v.implementing_agency = p.implementing_agency AND v.ls_term = p.ls_term
        WHERE p.ls_term = %s AND p.state = %s AND p.district = %s
        GROUP BY p.implementing_agency, v.vendor_count, v.top_vendor, v.top_vendor_share_pct
        ORDER BY in_queue DESC, works DESC
        """,
        args,
    )
    sectors = query(
        f"""
        SELECT COALESCE(sector, 'Other') AS sector, COUNT(*) AS works,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue
        FROM projects_scored {scope}
        GROUP BY 1 ORDER BY works DESC LIMIT 10
        """,
        args,
    )
    members = query(
        f"""
        SELECT mp_id, MAX(mp_name) AS mp_name, MAX(constituency) AS constituency,
               COUNT(*) AS works,
               COUNT(*) FILTER (WHERE overall_risk_score >= 40) AS in_queue,
               COALESCE(SUM(sanctioned_amount), 0) AS sanctioned
        FROM projects_scored {scope} AND mp_id IS NOT NULL
        GROUP BY mp_id ORDER BY works DESC LIMIT 12
        """,
        args,
    )
    top = query(
        f"""
        SELECT id, work_key, work_name, implementing_agency, mp_name, sector,
               work_status, sanctioned_amount, expenditure, delay_days,
               cost_deviation_pct, overall_risk_score, risk_level, flagged_reasons
        FROM projects_scored {scope} AND overall_risk_score IS NOT NULL
        ORDER BY overall_risk_score DESC, id
        LIMIT 15
        """,
        args,
    )
    findings = query(
        """
        WITH agencies AS (
            SELECT DISTINCT implementing_agency AS name FROM projects
            WHERE state = %s AND district = %s AND ls_term = %s
        )
        SELECT code, subject_type, subject, period, severity, headline
        FROM detector_findings
        WHERE ls_term = %s AND subject_type = 'agency'
          AND subject IN (SELECT name FROM agencies)
        ORDER BY severity DESC, code
        LIMIT 20
        """,
        [state, district, ls_term, ls_term],
    )
    return {
        "state": state,
        "district": district,
        "ls_term": ls_term,
        "works": works,
        "agencies": agencies,
        "sectors": sectors,
        "members": members,
        "top_flagged": top,
        "findings": findings,
    }
