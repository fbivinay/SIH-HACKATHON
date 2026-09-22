# Kasauti — MPLADS verification

SIH26102, Ministry of Statistics and Programme Implementation. Reads the
published MPLADS record, scores every work against comparable works, and hands
officials a ranked list of what to verify.

A *kasauti* is the touchstone a jeweller rubs gold against. It says which pieces
are worth assaying, never which are false. That is the claim this system makes
and the one it refuses, and most of the rules below are that sentence applied to
something concrete.

**Status: complete** (2026-09-21). Live at https://mplads-risk-monitor-web.vercel.app
(API https://mplads-risk-monitor.vercel.app), code at
https://github.com/fbivinay/SIH-HACKATHON, refreshed nightly. Built by
R Vinay Kumar and team (Git Happens). Everything below is how it works and the
rules that keep it working; each rule was learned from a real failure, which is
why most carry the measurement that found it.

---

## 0. The system at a glance

**Pages** (web, Next.js 16 App Router, in `web/app/`):

| Route | What it is | Rendering |
|---|---|---|
| `/` | Overview: hero + term switcher + six figures; the score's five parts; "What it will not tell you"; "Trends and early warnings" | static, 30-min revalidate |
| `/projects` | The review queue (score 40+), or every work with `risk_level=ALL`; status tiles, filters, decisions, CSV | dynamic (filters) |
| `/projects/[id]` | One work: score, reasons, peers, decision trail; `[id]` is a `work_key` or a serial | ISR, first visit |
| `/states` | Map of India first, then 36 states ranked | static |
| `/state/[state]`, `/district/[state]/[district]` | State and district desks | ISR (36 states prebuilt) |
| `/mps` | Every member: compare panel first, then cards | static |
| `/mp/[id]`, `/mps/compare` | Member desk; up to four members side by side | ISR; dynamic |
| `/provenance` | Sources: the architecture (animated), where the AI is, the four detectors | static |

Nav order: Overview, Projects, States, MPs, Sources. Old addresses redirect
(308): `/alerts` → `/projects`, `/map` → `/states`, `/analysis` → `/mps`. The
desks' `?ls_term=` is rewritten into the path (`/state/X/t/17`), see §12.

**Code:**
- `api/` — FastAPI on Vercel Python (`main.py`, `db.py`), tests in `api/test_api.py`.
- `data/` — `schema.sql`, `load_real_data.py` (loader), `scoring.py` (scorer),
  `detectors.py` (D-01..D-04), `sectors.py` + `llm_sectors.py` (sector
  labels), `vendors.py`, `mps.py`, `pg_retry.py`, `sector_cache.json`
  (committed), `snapshot/`, tests.
- `scripts/` — `fetch_mplads.py`, `apply_schema.py`, `classify_sectors.py`,
  `verify_mospi.py`, `verify_states.py`, `fetch_mp_profiles.py`,
  `build_sih_deck.py`, `preview_deck.py`, `screenshot.mjs`.
- `web/` — `app/` (routes), `components/`, `lib/` (`api.ts`, `format.ts`,
  `mpProfiles.ts`, `mpRows.ts`, `names.ts`, `terms.ts`), `data/mp_profiles.json`
  and `public/mps/*.webp` (committed, §9).
- `.github/workflows/refresh-data.yml` — the nightly refresh.

**The nightly refresh** (19:30 UTC, GitHub Actions, one run at a time): fetch
both terms from Empowered Indian → `apply_schema.py` (only if `schema.sql`
changed) → load (skipped if the extract is unchanged) → label new sectors with
Gemini (only with the `GEMINI_API_KEY` secret) and commit the cache → score
(skipped if the load was) → reconcile against MoSPI → refresh member profiles
from sansad.in and commit any change. A commit redeploys the site.

**Deploy:** two Vercel projects from one push to `main` — the web (root `web/`)
and the API (root `api/`, `vercel.json`). The web's build prerenders the static
pages and the 36 state desks against the live API.

**Commands:** API `cd api && python3 -m uvicorn main:app --port 8000`; web
`cd web && npm run build && npx next start -p 3100` (reads `web/.env.local`);
tests `python3 -m pytest data api -q` (147, live database, 3–6 minutes).

## 1. Never claim more than the record supports

The whole value of this project is that a flag can be argued with. One invented
number destroys that, and nobody downstream can tell which number it was.

- **Never invent a field the source does not publish.** MPLADS publishes no
  progress percentage, beneficiary count, geo-tag, or bill value. If a screen
  seems to want one, the answer is to say it is not published. The blind-spot
  list lives in `COMPLIANCE_BLIND_SPOTS` in `api/main.py`, served by
  `/api/compliance`, and its points are quoted in the overview's "What it will
  not tell you". A member MPLADS does not list yet shows "No MPLADS fund record
  published for them yet" — never a zero.
- **Never invent a guideline clause number.** The MPLADS guidelines are not in
  this repository. `basis` on each compliance rule says what the rule rests on
  in words; "clause 3.12.1" would look authoritative and be fiction.
- **A score is not an allegation.** It means a work does not resemble its peers.
  Every user-facing string about a score has to survive being read by the MP
  whose work it flags. The same holds for the forecast (§4): it is worded as a
  forecast from an agency's record, not a finding about any work.
- **Check the strength of a claim before showing it.** `similar_work_key` holds
  each work's nearest neighbour whatever the distance — set on 249,907 of
  250,839 works. The page printed "Similar to work #N" on all of them until it
  was gated on the 0.94 threshold. Before rendering a derived field, ask what it
  is set to when nothing interesting is happening.

## 2. `work_key` is the only identifier that survives a reload

`work_key` = `<Work ID>|<ls_term>|<IDA>`. `projects.id` is a serial the nightly
reload reassigns.

This has caused three separate bugs. Treat it as a standing rule: **anything
that outlives a load — a score, a review, a link target — is keyed on
`work_key`, never on `id`.**

- Work IDs restart per implementing agency, so `(Work ID, ls_term)` is not
  unique. 271 of 611 cross-file matches were in a different state and inherited
  a stranger's `start_date`, which feeds a quarter of the score. Hence the IDA.
- `project_scores` was keyed on `project_id` and only lined up because insert
  order happened to match. One work added upstream would have shifted every
  score silently.
- `similar_work_id` is a link target. Stale, it sends a reviewer to an unrelated
  work. Stored as `similar_work_key`, resolved back to an id in the view.

## 3. Source tables and derived tables are separate, and the swap is atomic

- `projects`, `expenditures`, `mps` — source facts, written once per load.
- `project_scores`, `agency_vendor_profile`, `detector_findings` — derived,
  rebuilt every run, no history.
- `work_reviews` (current decision per work) and `work_review_events` (every
  decision ever recorded) — written by reviewers, never by the pipeline.
- `projects_scored` is the view that joins them. **Read the view, never the
  tables**, except in `scoring.py`, which reads `projects` because it is about
  to replace its own previous output.

`write_scores` does `TRUNCATE` + `INSERT` **in one transaction**. That is what
lets the loader leave `project_scores` alone: a reader sees the whole previous
run or the whole new one, never an empty table. The loader used to truncate it,
which blanked every screen for the ~25 minutes until scoring caught up. Do not
reintroduce that, and do not split the commit.

Never `UPDATE` all of `projects` in a scoring pass. Postgres writes a new row
version per update; doing this once took the database from 300 MB to 457 MB
against Neon's 512 MB limit, recoverable only by a `VACUUM FULL` that needs room
for a full copy at the moment there is none.

**`TRUNCATE` inside a transaction holds the old file until COMMIT.** Measured on
2026-09-12: a 35 MB table showed +35 MB mid-transaction, +0 after. So the atomic
swap costs headroom equal to the table being replaced — 355 MB at rest + 150 MB
for `projects` = 505 MB against 512, and the 2026-09-11 nightly died with
`DiskFull` two thirds through the INSERT. Three things stand between the
pipeline and that wall, and all three must stay:

- **The loader skips the rewrite when the extract is unchanged.** It
  fingerprints the prepared frames (`extract_fingerprint`) and compares against
  `data_refresh.extract_sha256` of the most recent run that *wrote* — any status,
  not just success. A run that wrote and then failed has still changed the
  tables. `scoring.py` reads the same "unchanged:" note and does nothing
  (`SCORE_FORCE=1` overrides, e.g. after changing the scorer).
- **Both writers check headroom first** (`check_headroom`, and the guard in
  `write_scores`) and refuse with the arithmetic printed rather than die
  mid-INSERT. Refusing leaves the previous run intact; dying leaves an aborted
  transaction that then eats the "failed" mark too.
- **`work_name` is derived in the view, not stored.** It was `description[:60]`
  duplicated across 250,839 rows — 13 MB in the one table rewritten nightly, on
  a database 6 MB short. Never add a derived column to `projects`.

If the wall is hit again, the one-time way out is to compact in halves: move
half of `projects` to a side table, `VACUUM FULL` the remainder, move them back.
Peak extra is half the table, which fits when a whole one does not.

**The refresh must not fight the site.** The nightly rewrites tables the live
site is reading. A write that takes exclusive locks on two relations in turn
deadlocks with one ordinary read that took them in the other order — a
visitor's query on `projects_scored` holding the view and waiting for
`projects`, while the write holds `projects` and waits for the view. That
failed the 2026-09-20 nightly: the schema step re-applied all of `schema.sql`
every night, and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` takes an exclusive
lock even when there is nothing to add. So:
- `scripts/apply_schema.py` applies `schema.sql` only when its hash differs
  from the one recorded in `schema_applied` (`SCHEMA_FORCE=1` overrides); a
  normal night takes no schema locks at all. Verified by a manual run on
  2026-09-21: "schema unchanged — nothing applied, no locks taken".
- Every nightly write — the schema, the loader's three, the scorer's three —
  runs inside `data/pg_retry.py`'s `with_lock_retry`: `lock_timeout` 10s (a
  queued exclusive lock stalls every reader behind it), and on a deadlock or a
  lock timeout, roll back, wait, retry, up to six times. Each is a whole
  transaction that replaces what it touches, so a retry is safe. Wrap any new
  nightly write the same way.

## 4. Population statistics stay at population grain

Cohort detectors (`D-01`..`D-04` in `data/detectors.py`) describe an agency or a
Member of Parliament, not a work. **Never fold a detector finding into a work's
risk score.** An agency paying 99% of its invoices in March says nothing about
any single one of those invoices, and attaching it to one would be exactly the
kind of unfalsifiable accusation this project exists to avoid. They are shown
on the state, district and member desks, and described on Sources.

The same goes for the **forecast** (`/api/forecast/late`) and the "gone quiet"
early warning (`/api/trends`): both describe agencies and are never part of a
work's score.

The five weighted components in `data/scoring.py` are about the work itself:
cost 25%, delay 25%, duplicate 20%, agency 15%, compliance 15%. Bands: LOW < 40,
MEDIUM 40–70, HIGH ≥ 70. The queue is `>= 40` — one comparison, used everywhere;
an earlier `>` in one place put the overview and the queue 328 works apart.

## 5. Thresholds are measured, not borrowed

Every cutoff here was calibrated on this data's own distribution, and each one
carries a comment saying so. If you change one, re-measure and update the
comment.

- Duplicate similarity `0.94` — the foot of the genuine near-duplicate tail.
- Benford MAD floor `9.0`, ceiling `15.5` — **peer-relative**, because the
  population itself does not conform to Benford. A textbook constant here would
  flag everybody.
- Idle allocation floor `35%`, minimum 17 recommended works — the floor was 1,
  which flagged a member seated weeks ago with a single work.
- The forecast's cut is the day's own **75th percentile** of agencies' overdue
  share (agencies with 20+ open works; 64.7% on 2026-09-21, median 48%), not a
  constant. Completed works carry no due date, so an agency's past on-time
  record cannot be measured; its current backlog is the best evidence the
  record holds.
- Member matching (`fetch_mp_profiles.py`): a name must score ≥ 0.62 unless it
  is the only member on its seat that term, and no Parliament record may stand
  for two members in one term (§9).

## 6. Money comes from the source's own aggregates

Per-MP and per-state money figures are read from `mps`, not recomputed from
works. That is what lets any row be checked against empoweredindian.in — 36 of
36 states match exactly. Recomputing would be defensible and would break that
property, so don't.

Two rates that are not interchangeable: `paid_rate` (expenditure / allocated)
and `committed_rate` (recommended / allocated). The source publishes one number
under both names. Likewise `idle_amount` (never committed to any work) is not
`unspent_amount` (committed, awaiting payment).

## 7. Provenance is checked, not asserted

The problem statement designates `mplads.mospi.gov.in`. It serves totals, states
and member names openly; works only through an OTP-gated citizen rating form,
one member in one ward at a time. No bulk export exists. We load Empowered
Indian's export of the same record, and `scripts/verify_mospi.py` reconciles
against the official endpoints on every refresh.

**Keep that reconciliation running, and wherever it is reported, keep both hops
apart.** Ours-to-source is our responsibility; source-to-MoSPI is upstream lag.
Reporting one combined number invites reading all of it as our error, which it
is not. It is not displayed on the site (owner's call, 2026-09-21 — Sources
opens with the architecture instead), but it runs nightly and `/api/provenance`
serves both hops.

## 8. The language model labels, it does not judge

Gemini assigns a sector when the keyword rules cannot. That is all it does. It
never scores, ranks, or flags, and **no model output may become a risk number.**

It was chosen over embeddings because it can abstain — it answered "Other"
5,167 times rather than guessing. MiniLM always returns a nearest sector, which
is how "Muktidham" scored against water works.

Labels are cached in `data/sector_cache.json` (41,691), which is **deliberately
committed** so a clone gets them with no API key. Scoring is otherwise offline,
deterministic and free; keep it that way.

## 9. Who a member is comes from Parliament, not MPLADS

MPLADS publishes a member's money and works and nothing about the member.
`scripts/fetch_mp_profiles.py` reads sansad.in's Lok Sabha (17th, 18th) and
Rajya Sabha rosters, matches all 1,110 members in `mps`, and writes
`web/data/mp_profiles.json` (party, age, education, profession, terms) and
`web/public/mps/<mp_id>.webp` (120×150, ~4.4 MB for all), both committed.

- **A profile never feeds a figure, score or flag.** Money stays the portal's.
- **Personal data is never read**: the records carry personal phone numbers,
  e-mails, home addresses and family details; none reaches the output.
- Photos cannot be linked — sansad.in sends `Cross-Origin-Resource-Policy:
  same-site` — so they are stored, cropped to 4:5.
- **Sitting members MPLADS does not list yet** are kept under `unlisted`, keyed
  `ls-<id>` / `rs-<id>`: 14 on 2026-09-21 (13 Rajya Sabha members seated in
  2026, one Lok Sabha member), which is why the 18th lists 788 = 774 + 14.
- Matching lessons: the 17th roster lists members at their *current* seat;
  Rajya Sabha writes "Keralam", "National Capital Territory of Delhi" and
  "Nominated"; a seat with one member is not proof — Akhilesh Yadav won
  Azamgarh and moved, leaving Dinesh Lal Yadav alone on it.
- It runs **nightly** after the load. It writes nothing unless nine in ten
  members match, and leaves the file untouched when nothing changed, so a quiet
  night makes no commit.
- Member names shown anywhere go through `cleanName` (Parliament's spelling,
  `lib/mpProfiles.ts`, server only — the file is ~430 KB) or `cleanPortalName`
  (`lib/names.ts`, for the browser): the portal writes "(17LS)", "(EX17LS)",
  "(17th Lok Sabha)" into names.

## 10. Operational rules

- **One DB actor at a time.** `load_real_data.py` and `scoring.py` rewrite whole
  tables. Never run two concurrently, and do not start one while the nightly
  Action may be running (`gh run list`). A manual run is `gh workflow run
  refresh-data.yml`; the workflow's concurrency group queues a scheduled run
  behind it. GitHub often starts the 19:30 UTC schedule late.
- **Scoring takes ~50 minutes locally** and holds ~2.5 GB. It is not hung.
- **Parse every input frame before writing anything.** A `KeyError` on the
  fourth file once killed a load *after* it had committed 250,839 works.
- **Report silent producers.** A detector that writes nothing, a classifier
  batch that labels nothing — say so. Two separate bugs here looked like clean
  runs because failure was indistinguishable from "nothing to do".
- **Secrets live only in `.env`** (gitignored via `.env*`): `DATABASE_URL` and
  `REVIEW_TOKEN`. Never commit or print them. **Quote the values** —
  `DATABASE_URL` contains `&`, and unquoted, `. .env` backgrounds the line and
  silently leaves the variable unset.
- **No Gemini key is needed to run anything that already works.** A key belongs
  in the `GEMINI_API_KEY` GitHub secret, nowhere else; without it the labelling
  step prints why and skips, and new works land in "Other", a real peer group.
  Never put a key in `.env` on a shared machine or paste one into a chat. At
  ~22% of new descriptions needing a label, it costs 3–9 requests a day.
- **Run the tests before committing:** `python3 -m pytest data api -q` — 147,
  against the live database, 3–6 minutes.
- **A decision is a toggle, and clearing is not an event.** Pressing the
  decision a work already carries posts `status: "pending"`, which deletes its
  `work_reviews` row. "pending" is the absence of a decision, so it is not in
  `REVIEW_STATUSES` and not in either table's `CHECK`; the clearing leaves no
  row in `work_review_events`. All review rows were cleared on the owner's
  request on 2026-09-21 (backup kept outside the repository).
- **Never press a decision in a browser test.** The local web talks to the live
  API and the live database, so a scripted click on Escalate / Verified /
  Dismiss writes a real decision onto a real work the public site then shows.
  It happened once (2026-09-18) and had to be reversed by hand. Test the
  optimistic flip by reading `aria-pressed` without submitting.
- **A page that uses a new API endpoint is first built against the old API.**
  Web and API deploy from the same push at the same moment, so a static page
  prerenders against whatever API was live — the overview's forecast card was
  built before `/api/forecast/late` existed, and its `.catch(() => null)` left
  the card out. It heals at the next 30-minute revalidation; to heal it at
  once, redeploy the web project alone (`npx vercel redeploy <latest web
  deployment url> --target production`; `npx vercel ls mplads-risk-monitor-web`
  lists them).
- **Local verification.** `next start` serves the chunks it started with: after
  every `next build`, kill the server **by PID** (`ps -eo pid,args | grep
  next-server`) and start it again, or you will measure the previous build for
  an hour. `pkill -f "next start"` matches the shell that runs it and kills
  that instead. The API on :8000 and the web on :3100 are the local pair.
  Measure in a browser (playwright-core against `next start`), not by looking.

## 11. Interface

**Colour only ever means risk** — `--risk-low/medium/high`. Monochrome
otherwise. The deliberate exceptions, all on the owner's call: the words "AI
powered" are `--ai-red` wherever they appear and the dot beside them is
`--risk-low` green; the pointer is `--risk-high`; the logo
(`web/public/logo.png`, a tricolour K, also `web/app/icon.png`) takes no CSS
colour; and the State Emblem appears once, beside the Ministry's name in step 1
of the architecture on Sources — attribution of whose record this is, nothing
more. Its use is restricted by the State Emblem of India (Prohibition of
Improper Use) Act, 2005, so it appears nowhere else, and the footer's "not
affiliated with any ministry" must stay true beside it. Nothing else earns a
hue: asked for a coloured ring, the owner got ink at 45–55% — noticeable is a
matter of weight and contrast. Icons (lucide) and the stack's logos
(simple-icons) are drawn in ink.

**Light mode only** (owner, 2026-09-15): `:root { color-scheme: light }`,
`viewport.colorScheme` in `app/layout.tsx`, no `prefers-color-scheme: dark`
block anywhere. Do not bring the dark palette back.

**Phones are refused outright** (owner, 2026-09-15): the inline script at the
top of `<body>` sets `<html data-phone>` and `.phone-wall` shows one sentence in
place of the page. It must survive "Desktop site" on a phone, which rewrites the
user agent, so the second test is hardware: a coarse pointer on a screen taller
than 5:3. Do not replace it with a width query — the desktop-site viewport is
980px wide.

Geist and Geist Mono. `zoom: 1.33` at ≥1024px, `1.15` at 700–1023px, none
below. Tables scroll inside their own container; the page body never scrolls
sideways. Money is `formatINR` (₹ Cr / L), counts `formatCount`, timestamps in
IST with the label written literally. Every page names itself in the tab
(`metadata` / `generateMetadata`). `app/not-found.tsx` and `app/error.tsx` are
ours, not Next's bare defaults.

**Masthead**: ~125px, mark 74px, name 2rem; the nav links 0.95rem with 0.42rem
side padding so the mark, the name, five links and the search field fit at
1280 wide. **Site search** (`components/SiteSearch.tsx`) works at two speeds:
every state, district, agency and member (~3,200 names, 270 KB) comes from
`/api/search/index` once and is matched in the browser in the same frame
(29–94ms); works come from `/api/search/works`, debounced 140ms, aborted and
cached (0.8–1.1s locally, 29ms on a repeat). That endpoint deliberately does
not `ORDER BY` risk — sorting the whole match set took 2.1s against 0.7s — it
ranks its first 40 matches by where the query sits in the name. `/` focuses it.

**Every section with a link opens it from anywhere inside**
(`components/ClickableSections.tsx`, one delegated listener): a table row opens
its first link (its subject); a card, list item or article opens its link if
all its links go to one place; a section with several destinations is left
alone. Links, buttons, fields, `<summary>`, an open `<details>`, the decision
buttons and the map keep their own behaviour; selecting text never navigates;
ctrl/cmd/shift-click opens a tab; the pointer is marked by the same test.

**The pointer is the operating system's, in red** — two SVG cursor images in
CSS, drawn at hardware rate. A JavaScript dot-and-ring was always one to three
frames behind the hand and read as the whole site lagging (removed
2026-09-18). The clickable rule is `html :is(a, button, …)` at (0,1,1), because
component rules like `.review-btn { cursor: pointer }` beat a bare `button`.

### The overview — four screens

1. **Hero, term switcher and six figures**, filling the viewport between the
   masthead and the ticker with no slack. `.home-fold`'s height is measured by
   `components/FoldHeight.tsx`: `--fold-h` = `(innerHeight − masthead −
   ticker) / currentCSSZoom`, because `100dvh` under the root zoom was
   inconsistent (85px short at 1440×810, 47px long at 1366×768). The six
   figures are cards on a 3×2 grid on a light glass panel; two `max-height`
   queries (980px, 820px) keep the panel above the ticker (34–51px of air on
   six viewports). The term switcher is **not a navigation**: every scope is
   rendered on the server and handed to `components/FiguresBoard.tsx`, so a
   switch is `useState` + `history.replaceState`, zero requests (a `<Link>` and
   a `router.replace` both read as lag, because they were). `TERMS` lives in
   `lib/terms.ts` — a plain value exported from a `"use client"` module reaches
   the server as a client reference (`TERMS.find is not a function`).
2. **What the score is made of** (`.score-screen`, `components/ScoreMethod.tsx`)
   fills the second screen: `min-height: var(--fold-h)`, six cards on **auto
   rows left to the grid's default stretch** — `grid-auto-rows: 1fr` hung the
   second row 26–145px out of the slab, `align-content: space-between` left a
   hole. Type tiers by window height (900, 740) and width (1450); those
   queries see the window's pixels, not the zoomed ones.
3. **What it will not tell you** (`.limits-screen`): four limits, four points
   each, no "Read more" — every point a rule in `data/scoring.py`, an entry in
   `COMPLIANCE_BLIND_SPOTS`, or the forecast's rule. "It forecasts only from the
   record" replaced "It reports, it does not forecast" when the forecast went
   in. The heading and lede are one revealable block (`.section-intro`) so they
   arrive together.
4. **Trends and early warnings** (`components/WatchScreen.tsx`): money paid by
   month with March in full ink (`/api/trends`); **works likely to run late**
   (`/api/forecast/late`, §5); agencies **gone quiet** (20+ open works, nothing
   paid in 180 days); and the **compliance rules** with breach counts, linking
   to `/projects?risk_level=ALL&compliance=breach` — the same `compliance_risk
   > 0` test as the count. This screen is where the brief's "trend analysis",
   "early warning", "predictive insights" and "automated compliance
   monitoring" are visible; the alignment check on 2026-09-21 found all four
   missing until it was added. Do not remove it without replacing them.

Cards in screens 2–4 align top and foot (`margin-top: auto` on the last line);
centring left every title at a different height. The risk ticker runs on the
overview only, along the bottom (`OnHome` in `app/layout.tsx`), carrying only
the works. "AI powered" is visible on every page (masthead) and before "Why was
this flagged?" on the work page — the brief asks for an AI-powered system.

### Projects (the queue)

- The band select is also the scope: nothing chosen is the review queue (score
  40+), `risk_level=ALL` is every work, a named band is that band whatever its
  score. The summary endpoint defaults its floor to 40, so outside the queue
  the page passes `min_score=0`, or "All works" counted 48,296 and "Low" 0.
- The five **status tiles** are the review-status filter; pressing the one that
  is on takes it off; their counts are taken **without** the status filter, or
  pressing Escalated zeroed every other tile.
- **A row is one object**: a stretched link on the `<tr>` covers the work, the
  place, the money and the risk bar; district and state links, "Read more" and
  the decisions sit above it. First two lines bold; two reasons shown, the rest
  behind `<details>`. Rows do not zoom on hover (it shook the page at the foot
  of the queue); they tint.
- The filter bar is a **grid** — flex sized each select to its widest option
  and wrapped raggedly. The pager shows no "Previous" on page 1 and no noun.
- **The queue streams**: the filter bar and download render from the URL; the
  tiles and table stream behind `<Suspense>` keyed on the filters, with ghost
  fallbacks (first byte 20–40ms). A filter change is `router.replace` in
  `useTransition`: the bar carries `aria-busy`, a sweep runs along its edge,
  and the tiles and table drop to 45% (`.queue-screen:has(...)`), on screen
  156ms after the change.
- Decisions flip at once (`useOptimistic`); `app/projects/actions.ts` posts
  them server-side (the `REVIEW_TOKEN` never reaches the browser) and calls
  `updateTag("api")` so a reviewer reads their own write.
- The API keeps the queue's original names (`/api/alerts`,
  `/api/alerts/summary`, `/api/alerts/export`, `/api/alerts/review`).

### States, MPs, Sources

- **States** opens on the map (`components/StateMap.tsx` in `.map-screen`,
  sized by `--fold-h`, framed with `fitBounds` and `zoomSnap: 0.1` so India
  fills 88–95% of the height). Clicking a state opens its desk. Below, 36 state
  cards ranked in the browser (`components/StateRanking.tsx`, `?sort=` read
  after hydration). Paid rate and committed rate are shown apart (§6).
- **MPs** (`components/MpDirectory.tsx`): compare panel first — four slots, a
  search that fills them, the cards' "+ Compare" fills the same slots — then
  cards sixty at a time, filtered and sorted in the browser. Both terms arrive
  with the page, as packed arrays (`lib/mpRows.ts`: 836 KB of HTML became
  428 KB). `/mps/compare` is one term only: a member's two terms are two
  allocations. Rajya Sabha's term count says "in Rajya Sabha" — it counts only
  those. A record whose seat has since ended says "Seat ended".
- **Sources** (`/provenance`) opens on the architecture
  (`components/ArchitectureFlow.tsx`, the deck's slides 2–3 in the product's
  language, every count live). It **snakes** so each arrow joins consecutive
  steps: 1 → 2, down into 3 under the right end of 2, 3 → 4 right to left, down
  into 5 under the left end of 4, 5 → 6 → 7; each turn is a grid shaped like the
  row below it. Then "Where the AI is" (`components/WhereTheAI.tsx`, three
  points per model) and the detectors (two points each, what it measures and
  what it does not claim).

### The deck

`scripts/build_sih_deck.py` reads every figure from the database at build time
and refuses to build on a null or zero — it shipped stale twice when the
numbers were typed in. Its content is images (six diagram boards in
`docs/deck/diagrams/boards.template.html` with `{{tokens}}` filled from the
database, rendered by `render.mjs`, plus six screenshots). Exactly three links,
everywhere: demo video, prototype, GitHub. Use `fileURLToPath`, not
`new URL(import.meta.url).pathname` (the space in this repository's path was
percent-encoded into a parallel directory). No LibreOffice here:
`scripts/preview_deck.py` redraws the built `.pptx` as HTML — exact for
geometry, approximate for text wrapping; look at it before trusting a layout.

## 12. Performance

Measured on 2026-09-21 on the live site: every cached page answers in ~0.09s
(against 0.3–0.4s when rendered per request), repeat visits load in 0.2–0.75s
with the largest paint at 0.3–1.7s, and nav clicks land in 0.2–0.4s.

**Pages are built once and cached, not rendered per visit.** A page that reads
`searchParams` is rendered on every request; one whose inputs are all in its
path is served from the cache and **prefetched in full by every link to it**,
so the click is instant.
- `/`, `/states`, `/mps`, `/provenance` are static. None reads the request:
  `FiguresBoard`, `StateRanking` and `MpDirectory` read `?ls_term=`, `?sort=`,
  `?compare=` in the browser after hydration (server and first client render
  agree on the default, then the URL's choice lands).
- The desks and the work page are ISR: `generateStaticParams` returns `[]` (the
  state desk lists its 36 from the API, falling back to `[]`), so each path is
  rendered on first visit and cached. The desks' term moved from the query into
  the path **invisibly**: `beforeFiles` rewrites in `next.config.ts` serve
  `/state/X?ls_term=17` from `/state/X/t/17` (same for districts and members),
  so every existing link keeps its address.
- Only `/projects` and `/mps/compare` are dynamic, by nature. Never read the
  request in the others without meaning to make them dynamic; check the route
  table after `next build`: `○` or `●`, not `ƒ`.
- **A cached page must never cache a failure as "not found".** `lib/api.ts`
  throws `ApiError` with the status; pages call `notFoundOr(err)`, which shows
  the not-found page only for a real 404 and rethrows anything else. Found when
  a real work page was served as missing after one failed first render. A
  streamed not-found keeps status 200 (the root `loading.tsx` starts the stream
  first) but carries `noindex`.
- The build prerenders 45 pages against the live API. All at once that emptied
  the API's connection pool and failed a build, so `next.config.ts` builds two
  pages per worker at a time and retries a failed page three times. `get()` in
  `lib/api.ts` also retries once on a 5xx or a dropped connection.
- `lib/api.ts` caches every GET for 1800s under the tag `api` (the record
  changes nightly); `app/loading.tsx` answers a click in ~150ms. Member photos,
  the emblem and the logo are cached for a day (`headers()` in
  `next.config.ts`; Vercel serves `public/` with `max-age=0` by default).
- **The loading cover plays once every six hours** (below), and is 1.7s.

**The API's cost is the round trip to Neon, not the SQL.** A queue statement
executes in under 1ms (EXPLAIN ANALYZE 0.77ms); from a laptop the round trip is
~0.6s. Check with `SELECT 1` before optimising a query. What `api/db.py` does:
- **psycopg2 keeps at most `minconn` connections idle and closes any other on
  `putconn`** — at `minconn=1` every statement run beside another opened and
  threw away a connection (a 1.0–3.7s TLS handshake each). The pool is built at
  one (the constructor opens `minconn` in front of the first request, and one
  failed handshake failed that request — it broke a deploy), then `minconn` is
  raised to 4 and `_warm` opens the rest in the background.
- Reads end their transaction (`rollback`), so no connection goes back "idle in
  transaction"; TCP keepalives are set.
- A stale connection is discarded and the next tried, up to `minconn + 1`
  times — Neon closes idle connections together, and a single retry landed on
  the second dead one.
- `_borrow` queues up to 15s for a free connection rather than failing.
- `/api/alerts` runs its rows and its total in parallel; the total is
  remembered per filter set for 30 minutes (cleared by every decision); the
  rows query sets `work_mem` to 32MB (it spilled ~220 MB to disk); filters,
  the search index and the MP directory are memoised.

**Global helpers must stay cheap** — they run on every page.
- `WordLift` checks React's marker with `Object.keys`, never `for...in` (which
  walks hundreds of inherited properties per text node); cheap tests run first;
  the sweep stops once three pass empty after load; `[data-count]` (every
  `CountUp`) is skipped, or it was re-wrapped every frame of its count.
- `FoldHeight` watches the masthead and ticker with a ResizeObserver and re-runs
  per navigation. A MutationObserver on the whole body forced a layout after
  every DOM change anywhere (44ms in one click).
- `ClickableSections` finds the section first and searches for links only when
  it changes — `mouseover` fires for every word span.
- `CountUp` builds one `Intl.NumberFormat` per count, not one per frame.

## 13. Motion, measured

Every rule here was found by measuring in a headless browser, not by looking:
opacity and transform at every scroll position, frame intervals over 120
frames, scrollY through a reload. "Looks fine" was wrong six times.

**The loading cover** (`components/Splash.tsx`) is CSS-only — no state, no
effect, no `"use client"`; a version that hid itself from a `useEffect` sat at
0% on a slow hydration with no way to leave. It runs 1.7s: fill 1.2s on a
symmetric curve, fade 1.3 → 1.7s, `pointer-events: none` from the first fade
frame, `visibility: hidden` at the end. It plays **once every six hours**: the
inline script at the top of `<body>` keeps a timestamp in localStorage and on a
repeat visit sets `<html data-no-cover data-entered>` before first paint.
(It was 3.3s on every full load, which put the largest paint of six pages at
~5.2s.)

**Two kinds of entrance, and never retime a running one.**
- First load: the opening screen animates after the cover, from `--enter-at`
  (1400ms, half-way through the cover's fade).
- Client navigation: `<html data-entered>` sets `--enter-at: 0` and shorter
  travel (`--rise-y`, `--card-y`).
- `data-entered` is set at 2900ms (1400 + 390 stagger + 960), **after the last
  first-load entrance has ended**, or immediately on a navigation. Setting it
  while entrances run changes their `animation-delay`, and a running animation
  whose delay drops is retimed on the spot — every card snapped 47px → 0 in one
  frame. Never change `animation-delay`, `animation-name` or keyframe custom
  properties mid-animation. `ScrollReveal`'s last pass is at 1900ms. All are
  timed off the cover; move them together.

**Scroll reveals** (`[data-reveal]`, `@supports (animation-timeline: view())`):
- Two animations on one timeline: opacity over `cover 0px → 300px`, movement
  over `cover 0px → 680px`. One range could not serve both.
- **Pixel ranges, never percentages** — a percentage of `cover` on an 11,225px
  table was 5,093px of scrolling before solid.
- **Longhands, with `animation-duration: auto` written out.** Lightning CSS
  (under Tailwind v4) expands the shorthand with `0s`, a zero-length effect on
  a scroll timeline. Check the compiled chunk when one does nothing.
- The selector is `[data-reveal], .grid > [data-reveal]` — `.grid > .card`
  (0,2,0) outranks a bare attribute.
- `ScrollReveal` marks only blocks below the fold, **by layout position
  (`offsetTop` chain × `currentCSSZoom`), never `getBoundingClientRect`** — the
  rect includes the pending 104px entrance transform. It marks three times,
  add-only, and never inside another revealable block. Table rows never take a
  timeline.

**Scroll position.** `html { overflow-anchor: none }` — Chrome anchored on a
section still 74px low in its entrance and scrolled every reload 103px down.

**Everything under the pointer zooms** (owner, 2026-09-17): surfaces by
`--lift` (1.05, press 1.07); buttons, links and the single *word* under the
pointer by `--lift-text` (1.08); on `--t-lift`/`--ease-lift`, behind one
`hover / pointer: fine / prefers-reduced-motion: no-preference` gate. Change the
amounts in the tokens only. Words are wrapped in `.w` spans at runtime by
`components/WordLift.tsx` — **so never style running text with an element
selector like `.box span`**: it matches every word (`.archgov span { display:
block }` set a name one word to a line, and `.archdata__item span` shrank a
counter). Give the element a class. WordLift never takes a text node from React
(the original stays, emptied, and is rebuilt from when React writes into it)
and never touches a node React has not hydrated (it checks for
`__reactFiber$`; wrapping first was React error #418).

**The six figures drift**: ±8px, six periods from 4.6s to 6.6s with negative
delays, paused under the pointer, absent under reduced motion. On `transform`,
not `translate` — `translate` carries the hover lift, and an animation's fill
beats a declaration.

**The architecture runs**: packets travel every arrow (a wrapper the size of
its arrow translated by 100% of itself), the six nightly stations light in
turn, the step numbers pulse 1 to 7, the weight bars fill (25% = full) and a
needle sweeps the risk bar — transform and opacity only, 16.7ms median frames.
Paused unless `components/ArchLive.tsx` sets `[data-live]` (on screen); absent
under reduced motion.

**Performance budget**: 2 backdrop-filters on a page (masthead, ticker), no
`background-attachment: fixed`, `body::before` the one fixed wash layer; the
only gradient pseudo-elements are the ticker's two static end fades. What broke
it before: 17 backdrop-filters; a fixed background repainting every scroll
frame; a `mask-image` over something that moves every frame (the hero canvas,
then the ticker — each held the page near 30fps; the fades are painted once
now, and the ticker track has `will-change: transform`). `HeroField` draws at
30fps (its drift is 9px/s; its backing store is ~1.7M pixels). Anything that
keeps moving stops when off-screen or the tab is hidden (`HeroField`,
`ArchLive`).

**Zoom.** The root is zoomed. `clientX/Y` are screen pixels while elements move
in zoomed pixels — divide by `el.currentCSSZoom`. `getBoundingClientRect` is
zoom-adjusted, `offsetTop` and `clientWidth` are not (a canvas backing store is
`clientWidth × currentCSSZoom × devicePixelRatio`). `100dvh` at 1.33 rendered
1436px in a 1080px window, so `--zoom` is set beside `zoom` and
`.viewport-column` divides it out.

**Independent transform properties.** `scale` wraps `transform`: a ring at
`transform: translate(449px)` with `scale: 1.55` drew at 696px. Position with
`translate` when `scale` is in play.

**Sticky and stacking.** `.data-table thead th { top: 0 }` — the wrap owns the
scroll. `.topbar` is `z-index: 1100` because Leaflet stacks 200–1000.

**A headless screenshot is not the viewport.** With `--window-size=1440,810`
the page's `innerHeight` is 715 (Windows Chrome's own chrome is 95px) while
`--screenshot` renders 810 tall. Measure anything viewport-sized from a page
that loads the site in an iframe of a stated size.

---

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- Rebuild with `--code-only` unless an LLM key is available; and keep `graphifyy[sql]` installed, or `data/schema.sql` contributes nothing and the graph omits every table definition.
