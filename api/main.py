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
