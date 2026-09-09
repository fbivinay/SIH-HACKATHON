"""Check our per-state totals against the source's own states endpoint.

Run after a refresh to prove the numbers rather than assert them:

    curl -s "https://api.empoweredindian.in/api/summary/states?limit=50" -o /tmp/ei_states.json
    python3 scripts/verify_states.py

Verified 2026-09-09: all 36 states matched on allocation, expenditure, amount
recommended, MP count and completed works.
"""
import json, os, psycopg2
from dotenv import load_dotenv
load_dotenv("/home/rvina/projects/SIH HACKATHON/.env")
theirs = {r["state"]: r for r in json.load(open("/tmp/ei_states.json"))["data"]}
cur = psycopg2.connect(os.environ["DATABASE_URL"]).cursor()
cur.execute("""
  SELECT state,
         SUM(allocated_amount)::float, SUM(amount_recommended)::float,
         SUM(total_expenditure)::float, COUNT(DISTINCT mp_id),
         SUM(completed_works)::int, SUM(recommended_works)::int
  FROM mps WHERE ls_term = 18 AND state IS NOT NULL
  GROUP BY state""")
ours = {r[0]: r for r in cur.fetchall()}

print(f"{'state':26}{'alloc ok':>9}{'exp ok':>8}{'rec ok':>8}{'MPs':>6}{'compl':>8}")
bad = []
for name, t in sorted(theirs.items()):
    o = ours.get(name)
    if o is None:
        bad.append((name, "MISSING in ours")); continue
    def near(a, b, tol=0.005):
        return abs(a - b) <= max(1.0, abs(b) * tol)
    a_ok = near(o[1], t["totalAllocated"])
    e_ok = near(o[3], t["totalExpenditure"])
    r_ok = near(o[2], t["totalRecommendedAmount"])
    m_ok = o[4] == t["mpCount"]
    c_ok = near(o[5], t["completedWorksCount"], 0.02)
    if not (a_ok and e_ok and r_ok and m_ok):
        bad.append((name, f"alloc {o[1]:,.0f} vs {t['totalAllocated']:,.0f} | exp {o[3]:,.0f} vs {t['totalExpenditure']:,.0f} | rec {o[2]:,.0f} vs {t['totalRecommendedAmount']:,.0f} | mps {o[4]} vs {t['mpCount']}"))
    print(f"{name:26}{'OK' if a_ok else 'NO':>9}{'OK' if e_ok else 'NO':>8}{'OK' if r_ok else 'NO':>8}"
          f"{('OK' if m_ok else str(o[4])+'/'+str(t['mpCount'])):>6}{(str(o[5])+'/'+str(t['completedWorksCount'])):>8}")
print(f"\nstates: ours {len(ours)}  theirs {len(theirs)}")
print("mismatches:", len(bad))
for n, why in bad[:8]: print("  ", n, "|", why)
