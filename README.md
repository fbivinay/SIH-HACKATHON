# Kasauti — AI-powered MPLADS verification

A *kasauti* (कसौटी) is the touchstone a jeweller rubs gold against to judge it.
The stone destroys nothing and accuses nothing — it says which pieces are worth
assaying. That is the claim this system makes about an MPLADS work, and the one
it refuses to make.

Built for Smart India Hackathon 2026, problem statement **SIH26102** (Ministry
of Statistics and Programme Implementation): read the MPLADS record, score every
work against comparable works, detect cost overruns, delays, duplicates and
deviations from norms, and hand officials a ranked list of what to verify.

| | |
|---|---|
| Web | https://mplads-risk-monitor-web.vercel.app |
| API | https://mplads-risk-monitor.vercel.app/api/overview |
| Data | 250,839 works and 272,263 payments across the 17th and 18th Lok Sabha, refreshed nightly |
| Last refresh | 10 Sept 2026, 22:16 UTC — 250,839 loaded, 250,839 scored, 417 rows rejected |

---

## What it does

Every work in the published MPLADS record gets a **risk score from 0 to 100**,
built from five components that are each a property of the work itself:

| Component | Weight | What it measures | How |
|---|---|---|---|
| Cost | 25% | Sanctioned amount against the median for the same sector in the same district | Peer comparison, blended (`max`) with a scikit-learn **Isolation Forest** over amount, delay and spend |
| Delay | 25% | Days past expected completion | Published recommendation and completion dates; a work with no schedule scores 0, not high |
| Duplication | 20% | Near-identical wording to another work nearby | **Sentence-BERT** (`all-MiniLM-L6-v2`) embeddings, cosine ≥ 0.94, same district and sector |
| Agency | 15% | The implementing agency's delay rate, vendor concentration and oldest pending payment | Herfindahl-Hirschman index over the agency's vendor spend, per Lok Sabha term |
| Compliance | 15% | Deviations from the scheme's stated rules | Rule checks with the basis stated in words — never an invented clause number |

Bands: **LOW** < 40, **MEDIUM** 40–70, **HIGH** ≥ 70. The review queue is every
work at 40 and above. Today that is 48,296 works, 2,316 of them HIGH.

Sectors — the peer group a cost is compared inside — come from keyword rules
over the work description (22 named sectors), and where the rules cannot decide, from
**Gemini** (`gemini-flash-lite-latest`). The model labels; it never scores,
ranks or flags. Its 41,691 answers are cached in `data/sector_cache.json`,
which is committed so a clone scores correctly with no API key at all.

Four **cohort detectors** describe agencies and members rather than works, and
are shown separately, never folded into a work's score:

| | Detector | Finding |
|---|---|---|
| D-01 | Year-end payment burst | An agency paying most of its invoices in March |
| D-02 | First-digit anomaly | Sanction amounts whose leading digits diverge from their peers (Benford MAD, peer-relative) |
| D-03 | Idle allocation | A member with a large share of their allocation never committed to any work |
| D-04 | Uniform sanction amount | An agency sanctioning the same round figure again and again |

Every threshold was calibrated on this data's own distribution and carries a
comment in the code saying so.

## Where the data comes from, and how that is checked

The problem statement designates `mplads.mospi.gov.in`. That portal serves
totals, states and member names openly, but individual works only through an
OTP-gated citizen rating form, one member in one ward at a time; there is no
bulk export. We load **Empowered Indian's** export of the same record
(`scripts/fetch_mplads.py`, both terms explicitly — the API defaults to the
18th), and on every refresh `scripts/verify_mospi.py` **reconciles our figures
against the official dashboard's own endpoints**. Both hops are shown on
`/provenance`: ours-to-source, which is our responsibility, and
source-to-MoSPI, which is upstream lag. Per-state money figures are read from
the source's own aggregates rather than recomputed, so any row can be checked
against the source — `scripts/verify_states.py`, 36 of 36 states matching
exactly on allocation, expenditure, amount recommended, member count and
completed works.

## The nightly refresh

`.github/workflows/refresh-data.yml` runs at **19:30 UTC (01:00 IST)** on
GitHub Actions (Vercel functions cap at 300 s; scoring takes ~20 min on a
runner), against the same Neon Postgres the deployed API reads:

1. **Fetch** both terms from the source; fall back to the committed snapshot in
   `data/snapshot/` with a loud warning if the source produces nothing.
2. **Apply schema** (`data/schema.sql`, idempotent).
3. **Load** (`data/load_real_data.py`) — every input frame is parsed before
   anything is written; rejected rows are recorded, not dropped silently.
4. **Label new sectors** (`scripts/classify_sectors.py`) using the
   `GEMINI_API_KEY` repository secret, and **commit the cache** so the
   repository stays self-sufficient. Without the secret the step says why and
   skips; new works land in "Other", which is a real peer group.
5. **Score** (`data/scoring.py`) — writes `project_scores` with `TRUNCATE` +
   `INSERT` in **one transaction**, so readers see the whole previous run or the
   whole new one and the site is never blank while it works.
6. **Reconcile** against MoSPI and record the result in `source_reconciliation`.

Concurrency is locked to one run at a time. A killed run records itself as
failed rather than leaving the dashboard half-refreshed.

## The interface

Next.js 16.3.3, React 19.2, Tailwind v4, deployed on Vercel. Monochrome, Geist
and Geist Mono; colour means risk, with one deliberate exception — the words
"AI powered" are dark red and the dot beside them green.

Seven pages in the nav, in this order:

| Page | Route | What it holds |
|---|---|---|
| Overview | `/` | The headline figures with a term switcher, the risk split, **where the AI is** (the three models, each with what it decides and what it does not), what the score is made of, what it will not tell you |
| Alerts | `/alerts` | The review queue: every work ≥ 40, filterable by search, state, district, sector, band, term, status, minimum score and member; CSV export; a decision trail per work, written with a review token |
| States | `/states` | Every state ranked, with paid rate (expenditure / allocated) and committed rate (recommended / allocated) shown apart, because the source publishes one number under both names |
| Map | `/map` | Leaflet choropleth of risk by state |
| Works | `/projects` | The full record, filterable, with a range pager ("1–25 of 48,296") |
| Agencies | `/analysis` | Implementing agencies ranked by average risk with vendor share; the "gone quiet" list (no payment in 180 days); members ranked by idle allocation |
| Sources | `/provenance` | The reconciliation chain, the official interface (nine endpoints, which are open and which OTP-gated), rejects, and the blind spots — fields MPLADS does not publish (progress %, beneficiaries, geo-tags, bill values) and which the site therefore never invents |

Plus desks per state (`/state/[state]`), district (`/district/[state]/[district]`)
and member (`/mp/[id]`), and a page per work (`/projects/[id]`) headed
**AI powered · gemini-flash-lite — Why was this flagged?**, where each reason is
tagged with the method that produced it.

How it moves, and what that cost to get right:

- A **CSS-only loading cover** (3.3 s, a bar and a counting percentage) that
  cannot hang, because it depends on nothing that loads behind it. The page
  assembles in view as the cover lifts.
- **Scroll-driven arrivals** (`animation-timeline: view()`): opacity completes
  over 300 px of travel so text is solid while it is read, movement eases out
  over 680 px so the settle is visible. Only blocks below the fold at load take
  a timeline, marked by layout position rather than the drawn box.
- **Figures count up**, re-triggered on every viewport entry.
- A **risk ticker** in the masthead carrying the highest-scoring works.
- An instant **loading state** on every nav click, and API reads cached for
  five minutes so a click lands in 130–550 ms rather than the one to nine
  seconds a cold database query takes. Submitting a review expires the cache.
- A **field of drifting points** behind the overview headline — one 2D canvas,
  four hundred points, under a millisecond a frame, stopped when off-screen.
- A **dot-and-ring pointer** on devices with a fine pointer; the ring trails
  the dot, opens over links, closes when pressed, and steps aside for text
  fields.
- Every one of these was measured in a headless browser — frame intervals,
  opacity at every scroll position, scroll position through a reload — before
  it was called done. Two backdrop-filters on the whole page, no fixed
  backgrounds, no gradient pseudo-elements, 60 fps.

## The API

FastAPI + psycopg2, on Vercel Python. Every read goes through the
`projects_scored` view, which joins source tables to derived ones.

```
GET  /api/overview                 headline figures, ?ls_term=17|18
GET  /api/projects                 the record, filterable and paged
GET  /api/projects/{id}            one work
GET  /api/projects/by-key          one work by its stable work_key
GET  /api/filters                  filter options
GET  /api/map/states               risk by state for the map
GET  /api/states                   states ranked
GET  /api/states/{state}           state desk
GET  /api/districts                districts ranked
GET  /api/districts/{state}/{d}    district desk
GET  /api/mps                      members
GET  /api/mps/{mp_id}              member desk
GET  /api/agencies                 agencies with vendor concentration
GET  /api/alerts                   the review queue
GET  /api/alerts/summary           queue counts
GET  /api/alerts/export            the queue as CSV
POST /api/alerts/review            record a decision (X-Review-Token)
GET  /api/alerts/history           the decision trail for a work
GET  /api/detectors                the four cohort detectors and their limits
GET  /api/detectors/findings       their findings
GET  /api/trends                   time series, ?state=
GET  /api/compliance               the rule book and the blind spots
GET  /api/provenance               the reconciliation chain
GET  /api/data-freshness           when the last refresh finished
```

## Repository

```
api/            FastAPI service (main.py, db.py) and its tests
data/           schema.sql; load_real_data.py; scoring.py; detectors.py;
                sectors.py (keyword rules); llm_sectors.py (Gemini);
                vendors.py; mps.py; sector_cache.json (committed);
                snapshot/ (committed extracts); tests
scripts/        fetch_mplads.py; classify_sectors.py; verify_mospi.py;
                verify_states.py; build_sih_deck.py; screenshot.mjs
web/            Next.js app — app/ (routes), components/, lib/api.ts
docs/deck/      the SIH idea deck, built from the database by build_sih_deck.py
docs/superpowers/  original design spec and implementation plan
graphify-out/   a knowledge graph of the codebase (graphify)
.github/workflows/refresh-data.yml   the nightly refresh
CLAUDE.md       the rules this project learned the hard way
```

## Running it

Secrets live only in `.env` at the repository root, gitignored. **Quote the
values** — `DATABASE_URL` contains `&`.

```
DATABASE_URL="postgres://..."        # Neon
REVIEW_TOKEN="..."                   # lets the web app record decisions
```

`web/.env.local` points the web app at the API
(`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` locally). No Gemini key is
needed for anything that already works; it belongs only in the `GEMINI_API_KEY`
GitHub secret.

```
# API
cd api && pip install -r requirements.txt
python3 -m uvicorn main:app --port 8000

# Web
cd web && npm install && npm run dev

# Load and score against your own Postgres (~50 min for scoring, ~2.5 GB)
pip install -r data/requirements.txt
python3 scripts/fetch_mplads.py --out mplads-data
python3 data/load_real_data.py
python3 data/scoring.py

# Tests: 139, against the live database, ~2.5 minutes
python3 -m pytest data api -q
```

One database actor at a time: never run the loader and the scorer together,
and never start either while the nightly Action may be running.

## The deck

`scripts/build_sih_deck.py` fills the official SIH idea template
(`docs/deck/SIH26102-MPLADS-SIH-Idea.pptx`) with figures read from the database
at build time. It refuses to build on a null or zero, because it shipped stale
twice when the numbers were typed in.
