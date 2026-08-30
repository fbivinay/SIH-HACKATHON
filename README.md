# MPLADS Risk Monitor

This is the MPLADS Risk Monitor project for the SIH Hackathon. The project identifies and flags high-risk infrastructure projects based on cost, schedule, and compliance metrics.

See the [project specification](docs/superpowers/specs/2026-08-29-mplads-risk-monitor-design.md) and [implementation plan](docs/superpowers/plans/2026-08-29-mplads-risk-monitor.md) for details.

## Real data

The project runs on real MPLADS data pulled from the public MPLADS portal:
four CSVs (recommended works, completed works, expenditures, plus one lookup
file) totaling ~127k works, kept outside the repo in `MPLADS DATA/` (set
`MPLADS_DATA_DIR` to point at it if it's not a sibling of this repo). To
reproduce the load and scoring against Postgres (`DATABASE_URL` in `.env`):

```
data/.venv/bin/python data/load_real_data.py
data/.venv/bin/python data/scoring.py
```
