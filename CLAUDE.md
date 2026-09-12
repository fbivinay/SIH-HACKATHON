# Kasauti — MPLADS verification

SIH26102, MoSPI. Reads the published MPLADS record, scores every work against
comparable works, and hands officials a ranked list of what to verify.

A *kasauti* is the touchstone a jeweller rubs gold against. It says which pieces
are worth assaying, never which are false. That is the claim this system makes
and the one it refuses, and most of the rules below are that sentence applied to
something concrete.

---

## 1. Never claim more than the record supports

The whole value of this project is that a flag can be argued with. One invented
number destroys that, and nobody downstream can tell which number it was.

- **Never invent a field the source does not publish.** MPLADS publishes no
  progress percentage, beneficiary count, geo-tag, or bill value. If a screen
  seems to want one, the answer is to say it is not published. The blind-spot
  list lives in `COMPLIANCE_BLIND_SPOTS` in `api/main.py`, is served by
  `/api/compliance`, and is rendered on `/provenance` (the Compliance page that
  used to hold it was deleted). Add new limits there.
- **Never invent a guideline clause number.** The MPLADS guidelines are not in
  this repository. `basis` on each compliance rule says what the rule rests on
  in words; "clause 3.12.1" would look authoritative and be fiction.
- **A score is not an allegation.** It means a work does not resemble its peers.
  Every user-facing string about a score has to survive being read by the MP
  whose work it flags.
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
- `projects_scored` is the view that joins them. **Read the view, never the
  tables**, except in `scoring.py`, which reads `projects` because it is about
  to replace its own previous output.

`write_scores` does `TRUNCATE` + `INSERT` **in one transaction**. That is not an
accident and it is what lets the loader leave `project_scores` alone: a reader
sees the whole previous run or the whole new one, never an empty table. The
loader used to truncate it, which blanked every screen for the ~25 minutes until
scoring caught up. Do not reintroduce that, and do not split the commit.

Never `UPDATE` all of `projects` in a scoring pass. Postgres writes a new row
version per update; doing this once took the database from 300 MB to 457 MB
against Neon's 512 MB limit, recoverable only by a `VACUUM FULL` that needs room
for a full copy at the moment there is none.

**`TRUNCATE` inside a transaction holds the old file until COMMIT.** Measured on
2026-09-12: a 35 MB table showed +35 MB mid-transaction, +0 after. So the atomic
swap above costs headroom equal to the table being replaced — 355 MB at rest +
150 MB for `projects` = 505 MB against 512, and the 2026-09-11 nightly died with
`DiskFull` two thirds through the INSERT. Three things now stand between the
pipeline and that wall, and all three must stay:

- **The loader skips the rewrite when the extract is unchanged.** It
  fingerprints the prepared frames (`extract_fingerprint`) and compares against
  `data_refresh.extract_sha256` of the most recent run that *wrote* — any status,
  not just success. A run that wrote and then failed has still changed the
  tables; comparing against an older success skipped a rewrite while the table
  held a mutated row. `scoring.py` reads the same "unchanged:" note and does
  nothing (`SCORE_FORCE=1` overrides, e.g. after changing the scorer).
- **Both writers check headroom first** (`check_headroom`, and the guard in
  `write_scores`) and refuse with the arithmetic printed rather than die
  mid-INSERT. Refusing leaves the previous run intact; dying leaves an aborted
  transaction that then eats the "failed" mark too.
- **`work_name` is derived in the view, not stored.** It was `description[:60]`
  duplicated across 250,839 rows — 13 MB in the one table that is rewritten
  nightly, on a database 6 MB short. Never add a derived column to `projects`.

If the wall is hit again, the one-time way out is to compact in halves: move
half of `projects` to a side table, `VACUUM FULL` the remainder, move them back.
Peak extra is half the table, which fits when a whole one does not.

## 4. Population statistics stay at population grain

Cohort detectors (`D-01`..`D-04` in `data/detectors.py`) describe an agency or a
Member of Parliament, not a work. **Never fold a detector finding into a work's
risk score.** An agency paying 99% of its invoices in March says nothing about
any single one of those invoices, and attaching it to one would be exactly the
kind of unfalsifiable accusation this project exists to avoid.

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

**Keep that reconciliation running and keep both hops visible.** Ours-to-source
is our responsibility; source-to-MoSPI is upstream lag. Reporting one combined
number invites reading all of it as our error, which it is not.

## 8. The language model labels, it does not judge

Gemini assigns a sector when the keyword rules cannot. That is all it does. It
never scores, ranks, or flags, and **no model output may become a risk number.**

It was chosen over embeddings because it can abstain — it answered "Other"
5,167 times rather than guessing. MiniLM always returns a nearest sector, which
is how "Muktidham" scored against water works.

Labels are cached in `data/sector_cache.json`, which is **deliberately
committed** so a clone gets them with no API key. Scoring is otherwise offline,
deterministic and free; keep it that way.

## 9. Operational rules

- **One DB actor at a time.** `load_real_data.py` and `scoring.py` rewrite whole
  tables. Never run two concurrently, and do not start one while the nightly
  Action (19:30 UTC) may be running.
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
- **No Gemini key is needed to run anything that already works.** All 41,691
  sector labels are cached in `data/sector_cache.json`, which is committed, so
  a clone scores correctly with no key at all. Scoring and the API never read
  one.
- **A key belongs in the `GEMINI_API_KEY` GitHub secret, nowhere else.** The
  nightly Action labels descriptions a new extract introduces, between load and
  score, and commits the cache so the repository stays self-sufficient. Without
  the secret that step prints why and skips; the refresh still succeeds and new
  works land in "Other", which is a real peer group rather than a failure. Never
  put a key in `.env` on a shared machine and never paste one into a chat: at
  roughly 22% of new descriptions needing a label and a few hundred new works a
  day, this costs about 3-9 requests a day, which one account's free tier covers
  many times over.
- **Run the tests before committing:** `python3 -m pytest data api -q`. They hit
  the live database and take ~2.5 minutes.

## 10. Interface

Monochrome. **Colour only ever means risk** — `--risk-low/medium/high`. One
deliberate exception, on the owner's call: the two words "AI powered" are
`--ai-red` wherever they appear (eyebrow, badges, masthead, loading cover) and
the dot beside them is `--risk-low` green; the pointer is `--risk-high`. Nothing
else earns a hue. Geist and Geist Mono. `zoom: 1.33` at ≥1024px, `1.15` at
700–1023px, none below, because 456px of content does not fit a 390px phone.

Tables scroll inside their own container; the page body never scrolls
sideways — so nothing may be wider than the shell, including the hero canvas.
Money is `formatINR` (₹ Cr / L), counts are `formatCount`, and timestamps
render in IST with the label written literally.

Seven nav pages in this order: Overview `/`, Alerts `/alerts`, States
`/states`, Map `/map`, Works `/projects`, Agencies `/analysis`, Sources
`/provenance`. Signals, Rules and Trends were deleted; what they carried lives
on the overview and `/provenance`. "AI powered" must be visible on every page
(masthead) and in front of "Why was this flagged?" on the work page — the
brief asks for an AI-powered system and a visitor could not previously tell.

The deck (`scripts/build_sih_deck.py`) reads every figure from the database at
build time and refuses to build on a null or zero. It shipped stale twice when
the numbers were typed in. Do not retype them.

Its content is **images**, because the template's own instruction slide says to
use "points / diagrams / Infographics / pictures" rather than paragraphs. Six
diagram boards live in `docs/deck/diagrams/boards.template.html`, authored with
the product's tokens and fonts and rendered to PNG by `render.mjs`; six
screenshots of the running system sit beside them. The figures inside those
images are `{{tokens}}` the build fills from the database, so the no-retyping
rule survives the move to pictures. Exactly three links, everywhere: demo
video, prototype, GitHub.

Two things that bite here. `new URL(import.meta.url).pathname` keeps this
repository's space percent-encoded, so node wrote every PNG into a parallel
`SIH%20HACKATHON` tree and the deck silently kept using stale images - use
`fileURLToPath`. And there is no LibreOffice on this machine, so
`scripts/preview_deck.py` redraws the built `.pptx` as HTML and screenshots it;
it is exact for image and shape geometry and only approximate for text
wrapping. Look at the preview before believing a layout - it has caught an
image running a full inch off the slide, a title printing over the team badge,
and clipped captions that `verify()` could not see.

## 11. Motion, measured

Every rule here was found by measuring in a headless browser (playwright-core
against a local `next start`), not by looking. Keep doing that: sample
opacity and transform at every scroll position, frame intervals over 120
frames, scrollY through a reload. "Looks fine" was wrong six times.

**Two kinds of entrance, and never retime a running one.**
- First load: everything on the opening screen animates on a timer after the
  loading cover, starting at `--enter-at` (3000ms) — before that the cover is
  opaque and the entrance plays for nobody.
- Client navigation: `<html data-entered>` sets `--enter-at: 0` and shorter
  travel (`--rise-y`, `--card-y`), because the new page has no cover and sat
  blank for three seconds otherwise.
- `data-entered` is set at 4500ms, **after the last first-load entrance has
  ended**, or immediately on a navigation. Setting it while entrances run
  changes their `animation-delay`, and a running CSS animation whose delay
  drops by 3s is retimed on the spot — measured, every card snapped 47px → 0
  in one frame. Never change `animation-delay`, `animation-name` or keyframe
  custom properties on an element mid-animation.

**Scroll reveals** (`[data-reveal]`, `@supports (animation-timeline: view())`):
- Two animations on one timeline: opacity over `cover 0px → 300px`, movement
  over `cover 0px → 680px` with `--ease`. One range could not serve both —
  short and the arrival was invisible, long and text sat translucent while
  read.
- **Pixel ranges, never percentages.** A percentage of `cover` on an
  11,225px table was 5,093px of scrolling before solid.
- **Longhands, with `animation-duration: auto` written out.** Lightning CSS
  (under Tailwind v4) expands the `animation` shorthand and fills the
  duration as `0s`, which for a scroll timeline is a zero-length effect —
  blocks snapped 0 → 1 the instant their range began. Check the compiled
  chunk in `.next/static/chunks/*.css` when a scroll animation does nothing.
- The selector is `[data-reveal], .grid > [data-reveal]`: `.grid > .card`
  (0,2,0) outranks a bare attribute (0,1,0), and the first card of every
  grid on the overview never took a timeline until this was added.
- `ScrollReveal` marks only blocks below the fold at load, **by layout
  position (`offsetTop` chain × `currentCSSZoom`), never
  `getBoundingClientRect`** — the rect includes the pending 104px entrance
  transform, and a row at 599px was read as 765px, marked, and stuck at 61%
  opacity in the first viewport. It marks three times (rAF, `fonts.ready`,
  after the cover), add-only. Nothing nested inside another revealable block
  is marked: two nested fades multiply.
- Table rows never take a timeline; the wrap animates as one object.

**Scroll position.** `html { overflow-anchor: none }`. Chrome picked the first
section as scroll anchor while it was 74px low in its entrance and "kept it
in place" by scrolling every reload 103px down. Nothing here loads in above
the reader, so anchoring guards against nothing.

**The loading cover** (`components/Splash.tsx`) is CSS-only — no state, no
effect, no `"use client"`. The first version hid itself from a `useEffect`
timer and sat at 0% for three seconds on a slow hydration with no way to
leave. It runs 3.3s: fill 2.5s on a symmetric curve, fade 2.7 → 3.3s,
`pointer-events: none` from the first fade frame, `visibility: hidden` at the
end. `ScrollReveal`'s last pass and `data-entered` are timed off it.

**Performance budget, measured on `/alerts`:** 2 backdrop-filters on the
whole page (masthead, ticker), 0 `background-attachment: fixed`, 0 gradient
pseudo-elements, 60fps. What broke it before: 17 backdrop-filters, a fixed
body background repainting on every scroll frame, a CSS `mask-image` over a
canvas that repaints every frame (33ms frames → 16.7ms without; the fade is
done per point instead), and a canvas reaching under the masthead so its
backdrop blur recomputed every frame. `body::before` is the one fixed wash
layer. Anything that keeps drawing must stop when off-screen or the tab is
hidden (`HeroField`, `Cursor` both do).

**Zoom.** The root is zoomed, and it bites twice. `clientX/Y` are screen
pixels while elements move in the root's zoomed pixels — divide by
`el.currentCSSZoom`. `getBoundingClientRect` is zoom-adjusted, `offsetTop`
and `clientWidth` are not — a canvas backing store is `clientWidth ×
currentCSSZoom × devicePixelRatio`.

**Independent transform properties.** `scale` wraps `transform`: a ring at
`transform: translate(449px)` with `scale: 1.55` drew at 696px. Position with
the `translate` property (applied outermost) when `scale` is also in play.

**Sticky and stacking.** `.data-table thead th { top: 0 }` — the wrap owns the
scroll, so a topbar offset parks the header across row 1. `.topbar` is
`z-index: 1100` because Leaflet stacks 200–1000 and painted over the nav at
40. The pointer is 10000, above the cover at 9999.

**Navigation.** `app/loading.tsx` answers a click in ~150ms; `lib/api.ts`
caches every GET for 300s under the tag `api` (the record changes nightly),
and `app/alerts/actions.ts` calls `updateTag("api")` after a review so the
reviewer reads their own write. Measured: 130–550ms per click warm, against
1.3–9.3s cold plus 3.5s blank before.

**Local verification.** `next start` serves the chunks it started with: after
every `next build`, kill the server **by PID** (`ps -eo pid,args | grep
next-server`) and start it again, or you will measure the previous build for
an hour. `pkill -f "next start"` matches the shell that runs it and kills
that instead. The API on :8000 and the web on :3100 are the local pair; the
web reads `web/.env.local`.

---

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- Rebuild with `--code-only` unless an LLM key is available; and keep `graphifyy[sql]` installed, or `data/schema.sql` contributes nothing and the graph omits every table definition.
