# Kasauti

A kasauti (कसौटी) is the touchstone a jeweller rubs gold against to judge it.
The stone destroys nothing and accuses nothing - it says which pieces are worth
assaying. That is the claim this system makes about an MPLADS work, and the one
it refuses to make.

Built for Smart India Hackathon 2026, problem statement SIH26102: read the
MPLADS record, score the works that do not resemble their peers, and hand
officials a ranked list of what to verify.

Live at https://mplads-risk-monitor-web.vercel.app

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
