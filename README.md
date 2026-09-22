<p align="center"><img src="web/public/logo.png" width="170" alt="Kasauti"></p>

<h1 align="center">Kasauti — AI-powered MPLADS verification</h1>

<p align="center">
  <b>Smart India Hackathon 2026 · Problem Statement SIH26102 · Ministry of Statistics and Programme Implementation</b><br>
  Team <b>Git Happens</b> · built by R Vinay Kumar and team
</p>

<p align="center">
  <a href="https://mplads-risk-monitor-web.vercel.app"><b>Live prototype</b></a> ·
  <a href="https://youtu.be/0_Fwr7USExc"><b>Demo video</b></a> ·
  <a href="https://github.com/fbivinay/SIH-HACKATHON"><b>GitHub</b></a> ·
  <a href="https://mplads-risk-monitor.vercel.app/api/overview">API</a>
</p>

## Demo video

<p align="center"><a href="https://youtu.be/0_Fwr7USExc"><img src="https://img.youtube.com/vi/0_Fwr7USExc/maxresdefault.jpg" width="820" alt="Watch the Kasauti demo on YouTube"></a><br>
<sub>2 min 30 s · recorded on the live site · voice-over and captions · <a href="https://youtu.be/0_Fwr7USExc">watch on YouTube</a></sub></p>

---

A *kasauti* (कसौटी) is the touchstone a jeweller rubs gold against. The stone
destroys nothing and accuses nothing — it says which pieces are worth assaying.
That is the claim this system makes about every MPLADS work, and the one it
refuses to make.

Kasauti reads the **entire published MPLADS record**, scores every work against
comparable works, explains every flag in the record's own figures, and hands
Members of Parliament, State Nodal Authorities, District Authorities and the
Ministry a ranked list of what to verify — refreshed every night.

| The record, as of 21 Sept 2026 | |
|---|---|
| Works analysed | **2,50,839** (17th and 18th Lok Sabha) |
| Vendor payments analysed | **2,72,263** |
| Works in the review queue (score 40+) | **48,296**, of which **2,316** high risk |
| Works likely to run late (next 90 days) | **1,800** at 132 agencies |
| Works breaching a compliance rule | **37,284** |
| Members of Parliament | **788** in the 18th Lok Sabha, with photographs |
| Refresh | nightly, 01:00 IST |

---

## The problem, and how Kasauti answers it

The problem statement asks for an AI-powered platform that detects anomalies,
fraud and inefficiencies in MPLADS works. Here is where each part of the brief
lives in the system:

| The brief asks for | Kasauti |
|---|---|
| ML, AI and advanced analytics | Isolation Forest, Sentence-BERT embeddings, Gemini, and four statistical detectors |
| Cost overruns and deviations from norms | Every work's cost against the median of the same sector in the same district, plus an Isolation Forest |
| Duplicate works | Near-identical descriptions in the same district and sector (Sentence-BERT, similarity ≥ 0.94) |
| Delayed projects | Days past the completion date the record publishes |
| Irregularities in fund utilisation and payments | Agency vendor concentration and unpaid bills; year-end payment bursts; first-digit (Benford) anomalies; idle allocation; uniform sanction amounts |
| Risk-based alerts, high-risk cases highlighted | A ranked review queue with the reason for every flag, decisions and an audit trail |
| Trend analysis | Money paid month by month, and how much lands in March, the year-end |
| Early warning | Agencies holding open works that have paid nobody in 180 days |
| Predictive insights | Works likely to miss their due date, from their agency's own record |
| Automated compliance monitoring | Scheme rules checked on every work every night, with breach counts |
| Dashboards for MPs, State Nodal Authorities, District Authorities, the Ministry | A desk for every member, every state and every district, and a national overview |
| Transparency, accountability, less manual monitoring | Every figure traceable to the record; CSV export of any filtered queue; nightly automation |

---

## How a work is scored

Every work gets a **risk score from 0 to 100**, built from five components, each
a property of the work itself:

| Component | Weight | What it measures |
|---|---|---|
| **Cost** | 25% | Sanctioned amount against the median for the same sector in the same district (at least eight comparable works), blended with an **Isolation Forest** over amount, delay and spend |
| **Delay** | 25% | Days past the expected completion date; a work with no published schedule scores zero, not high |
| **Duplication** | 20% | Near-identical wording to another work nearby — **Sentence-BERT** (`all-MiniLM-L6-v2`) cosine similarity ≥ 0.94, same district and sector |
| **Agency** | 15% | The implementing agency's delay rate, vendor concentration (Herfindahl-Hirschman index over its payments) and oldest unpaid bill |
| **Compliance** | 15% | The scheme's checkable rules, each stating in words what it rests on |

Bands: **Low** below 40 · **Medium** 40–70 · **High** 70 and above. The review
queue is every work at 40 and above.

A work's peers are defined by its **sector**, read from its description by
keyword rules and, only where the rules cannot decide, by **Gemini**. Gemini
labels; it never scores, ranks or flags, and it is allowed to answer "Other" —
it did so 5,167 times rather than guess. All 41,691 of its answers are cached in
the repository, so the system scores identically with no API key.

**Every threshold was measured on this data's own distribution**, not borrowed
from a textbook, and each carries a comment in the code saying how.

### Beyond the score: patterns across agencies and members

Four detectors describe an **agency or a member**, not a work, and are never
added to any work's score — a pattern across an agency says nothing about any
single one of its works:

| | Detector | Looks for |
|---|---|---|
| D-01 | Year-end payment burst | An agency paying a large share of its year's invoices in March |
| D-02 | First-digit anomaly | Payment amounts that stray from Benford's law, ranked against other agencies (the whole population fails the textbook test) |
| D-03 | Idle allocation | A member's allocation never committed to any work, well above the typical share |
| D-04 | Uniform sanction amount | An agency sanctioning one identical figure again and again |

### Trends, the forecast and early warnings

- **When the money moves** — payments month by month; the share paid in March
  fell from 37.7% to 12.0% to 9.5% over three years.
- **Likely to run late** — works due in the next 90 days at agencies in the worst
  quarter by how many of their open works are already overdue (the cut is that
  day's 75th percentile). Completed works in the record carry no due date, so
  an agency's past on-time record cannot be measured; its current backlog is
  the best evidence the record holds. A forecast about agencies, never part of
  a work's score.
- **Gone quiet** — agencies holding 20 or more open works that have paid nobody
  in 180 days: money committed where nothing is moving.
- **Compliance, checked every night** — every rule with its breach count, and
  one click to the breaching works.

### What it will not tell you

- **It does not allege wrongdoing.** A score is a comparison — it says a work
  does not resemble works like it. Every flag names the rows it came from, so
  it can be argued with.
- **It invents no fields.** MPLADS publishes no progress percentage,
  beneficiary count, geo-tag or bill value, so none is shown. The source
  publishes one figure per completed work as both sanction and expenditure, so
  an overspend-against-sanction rule cannot fire, and the site says so.
- **It forecasts only from the record**, never from assumptions, and no
  forecast enters a score.
- **No model decides alone.** The score is deterministic and rule-weighted; no
  model output becomes a risk number.

---

## The site

Next.js 16 on Vercel. Light, monochrome, and **colour only ever means risk**.
Desktops, laptops and tablets only — phones are shown a note instead, even with
"Desktop site" switched on.

| Page | What it holds |
|---|---|
| **Overview** `/` | The national figures with a term switcher (17th, 18th, both); how the score is made; what it will not tell you; trends and early warnings |
| **Projects** `/projects` | The review queue — or every work — with search, state, band, term and review-status filters; status tiles that filter; the reasons for every flag; **Escalate / Verified / Dismiss** decisions (press again to clear) with an audit trail; CSV download of any filtered set |
| **One work** `/projects/[id]` | Why it was flagged: each component, its comparable works, the reasons, and the decision history |
| **States** `/states` | A risk map of India filling the first screen; click any state for its desk; every state ranked by paid-out, committed, completion, allocation or works to verify |
| **State desk** `/state/[state]` | The state's money, its districts, its members, what the money built, population-level signals and its highest-scoring works |
| **District desk** `/district/[state]/[district]` | Its implementing agencies with vendor concentration, its members, what was built, agency signals and works to look at first |
| **MPs** `/mps` | All 788 members of the 18th Lok Sabha (and the 17th), with photographs, party, house and seat; search, filters and sorting; **compare up to four side by side** |
| **Member desk** `/mp/[id]` | Allocation, committed, paid, never committed and awaiting payment; works; sectors; flags at member level; highest-scoring works |
| **Sources** `/provenance` | An animated diagram of how the system works end to end, where the AI is, and what each detector does and does not claim |

Also: a **site-wide search** (press `/`) over every state, district, agency,
member and work; **every row and card opens from anywhere inside it**; and a
proper not-found and error page.

**Who a member is** comes from Parliament's own records at sansad.in — party,
age, education, profession, terms and photograph — matched to all 1,110 members
in the record and refreshed nightly. Sitting members the MPLADS portal does not
list yet are shown with their profile and the words "No MPLADS fund record
published for them yet", never a zero. Personal phone numbers, e-mail
addresses, home addresses and family details in those records are never read.

### Fast by construction

Pages that do not depend on a query are built once and served from Vercel's
edge cache, and every link prefetches its page in full, so a click is instant.
Measured on the live site: cached pages answer in about **0.09 s**, repeat visits
load in 0.2–0.75 s, and navigation lands in 0.2–0.4 s. Everything that moves is
transform- and opacity-only, pauses when off screen, and is absent for visitors
who prefer reduced motion.

---

## Where the data comes from

The problem statement designates `mplads.mospi.gov.in`. That portal serves
totals, states and member names openly, but individual works only through an
OTP-gated citizen form, one member in one ward at a time — there is no bulk
export. Kasauti therefore loads **Empowered Indian's** machine-readable export
of the same record, and **reconciles its figures against the official MoSPI
dashboard's own endpoints every night**, keeping two differences apart: ours
against the source (our responsibility) and the source against MoSPI (upstream
lag). Per-state and per-member money figures are the source's own aggregates,
not recomputed — 36 of 36 states match exactly.

## The nightly refresh

`.github/workflows/refresh-data.yml` runs every night at 19:30 UTC (01:00 IST)
on GitHub Actions, against the Neon Postgres database the live API reads:

1. **Fetch** both Lok Sabha terms from the source.
2. **Apply the schema** — only if it has changed, so a normal night takes no
   locks on the tables the site is reading.
3. **Load** — every input file is validated before anything is written; bad
   rows are recorded with a reason, never dropped silently; nothing is
   rewritten if the extract is unchanged.
4. **Label new sectors** with Gemini, and commit the labels to the repository.
5. **Score** every work, swapped in with one transaction so the site is never
   blank while it works.
6. **Reconcile** against the MoSPI dashboard.
7. **Refresh member profiles** from Parliament's records, and commit any change.

Every write retries on a lock conflict with a visitor's query, one run at a
time is enforced, and a failed run records itself as failed.

---

## Built with

| | |
|---|---|
| Interface | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Leaflet — on Vercel |
| API | FastAPI (Python), psycopg2 — on Vercel |
| Data | PostgreSQL (Neon), pandas |
| AI and statistics | scikit-learn (Isolation Forest), Sentence-BERT (`all-MiniLM-L6-v2`), Google Gemini, Benford analysis, Herfindahl-Hirschman index |
| Automation | GitHub Actions (nightly), Vercel (deploy on every push) |

## Repository

```
api/        FastAPI service (main.py, db.py) and its tests
data/       schema.sql · load_real_data.py (loader) · scoring.py (scorer) ·
            detectors.py · sectors.py + llm_sectors.py · vendors.py · mps.py ·
            pg_retry.py · sector_cache.json (committed) · snapshot/ · tests
scripts/    fetch_mplads.py · apply_schema.py · classify_sectors.py ·
            verify_mospi.py · fetch_mp_profiles.py — the nightly refresh's steps
web/        Next.js app — app/ (pages), components/, lib/,
            data/mp_profiles.json and public/mps/ (member photographs)
docs/deck/  the SIH idea deck and the architecture diagram
.github/workflows/refresh-data.yml   the nightly refresh
CLAUDE.md   how the system works, and the rules it learned the hard way
```

## Running it

Secrets live only in `.env` at the repository root (gitignored). Quote the
values — the database URL contains `&`.

```
DATABASE_URL="postgres://..."     # Neon Postgres
REVIEW_TOKEN="..."                # lets the web app record decisions
```

`web/.env.local` points the web app at the API
(`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` locally). No Gemini key is
needed to run anything; the sector labels are committed.

```bash
# API
cd api && pip install -r requirements.txt
python3 -m uvicorn main:app --port 8000

# Web
cd web && npm install && npm run dev

# Load and score against your own Postgres (scoring takes ~50 minutes)
pip install -r data/requirements.txt
python3 scripts/fetch_mplads.py --out mplads-data
python3 scripts/apply_schema.py
python3 data/load_real_data.py
python3 data/scoring.py

# Tests — 147, against the live database, 3–6 minutes
python3 -m pytest data api -q
```

Run one database writer at a time: never the loader and the scorer together,
and never while the nightly refresh may be running.

---

<p align="center">
  Kasauti says which works are worth a site visit — never which are false.<br>
  MPLADS programme data via Empowered Indian, which aggregates the official MoSPI portal.
  Not affiliated with any ministry.
</p>
