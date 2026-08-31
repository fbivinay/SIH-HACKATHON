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


@app.get("/api/agencies")
def agencies(ls_term: Optional[int] = Query(None, ge=17, le=18)):
    """One row per agency per Lok Sabha term.

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
        ORDER BY w.avg_risk_score DESC
        """,
        params,
    )


@app.get("/api/mps")
def mps(limit: int = Query(100, le=1000)):
    """MPs by the value of their allocation still unspent.

    utilization_pct and unspent_amount come straight from the source's own
    published per-MP aggregates, not from anything computed here, so they can be
    checked against empoweredindian.in for the same MP.

    Sorted by unspent amount rather than by utilisation: the lowest utilisation
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
               m.allocated_amount, m.total_expenditure, m.utilization_pct,
               m.unspent_amount, m.completion_rate_pct, m.pending_payments,
               COALESCE(w.total_projects, 0) AS total_projects,
               COALESCE(w.high_risk_works, 0) AS high_risk_works
        FROM mps m
        LEFT JOIN work_stats w USING (mp_id, ls_term)
        WHERE COALESCE(m.allocated_amount, 0) > 0
        ORDER BY m.unspent_amount DESC NULLS LAST
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
