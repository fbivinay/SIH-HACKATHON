# Graph Report - SIH HACKATHON  (2026-09-12)

## Corpus Check
- 94 files · ~864,550 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 987 nodes · 1548 edges · 88 communities (52 shown, 33 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dd04cc73`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- classify_sector
- compliance_risk_score
- query
- test_detectors.py
- load_real_data.py
- Frontend Dependencies
- Vendor Concentration Tests
- Database Schema
- build_sih_deck.py
- api.ts
- [state]/page.tsx
- TypeScript Config
- format.ts
- layout.tsx
- MPLADS Risk Monitor — Design Spec (SIH26102)
- test_load_real_data.py
- MoSPI Figure Verification
- formatCount
- What You Must Do When Invoked
- MPLADS Data Fetcher
- test_current_refresh_run_id_ignores_an_abandoned_run
- scoring.py
- _a_state
- Brag Plan: Kasauti
- ProjectFilters
- Synthetic Data Generator
- Vercel Deploy Config
- State Totals Verification
- Overview Count Consistency Test
- Agency Average Bounds Test
- Weighted Paid Rate Test
- Compliance Rule Separation Test
- Uncheckable Rules Test
- Durable Project Key Test
- Project Pagination Test
- Durable Key Exposure Test
- Provenance Chain Test
- test_provenance_gap_stays_small
- test_quiet_agencies_hold_open_works_and_have_stopped_paying
- test_mp_dashboard_scopes_everything_to_one_member
- Review Token Fail-Closed Test
- diagrams/package.json
- ESLint Config
- PostCSS Config
- _RecordingCursor
- Kasauti — MPLADS verification
- projects/[id]/page.tsx
- test_scoring.py
- graphify reference: extra exports and benchmark
- add_base_features
- Data snapshot
- attach_agency_profile
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- web/README.md
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- test_state_desk_totals_agree_with_its_own_district_table
- test_the_state_desk_orders_members_by_the_column_it_claims
- test_provenance_reject_counts_come_from_the_latest_extract
- test_a_member_can_be_handed_their_own_queue
- .claude/CLAUDE.md
- extraction-spec.md
- mp_key
- MPLADS Risk Monitor Implementation Plan
- test_loaded_fingerprint_follows_what_was_written_not_what_succeeded
- app/page.tsx
- AGENTS.md
- build_rows
- alerts/page.tsx
- build.py
- Hyperframes Composition Brief: Kasauti
- Kasauti — AI-powered MPLADS verification
- build_mp_rows
- fetch_expenditures
- states/page.tsx
- preview_deck.py
- The two-minute explainer
- brag-output/composition/assets/README.md
- video-explainer/composition/assets/README.md
- fetch_mps
- write_detector_findings
- test_agency_risk_takes_the_worst_signal_not_a_blend

## God Nodes (most connected - your core abstractions)
1. `query()` - 33 edges
2. `formatCount()` - 31 edges
3. `formatINR()` - 21 edges
4. `riskLevelLabel()` - 18 edges
5. `classify_sector()` - 17 edges
6. `riskLevelClass()` - 16 edges
7. `compilerOptions` - 16 edges
8. `normalize()` - 15 edges
9. `api` - 15 edges
10. `Brag Plan: Kasauti` - 15 edges

## Surprising Connections (you probably didn't know these)
- `set_review()` --references--> `post()`  [EXTRACTED]
  api/main.py → scripts/verify_mospi.py
- `main()` --calls--> `normalize()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `unclassified_descriptions()` --calls--> `normalize()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `main()` --calls--> `classify_sector()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `unclassified_descriptions()` --calls--> `classify_sector()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py

## Import Cycles
- None detected.

## Communities (88 total, 33 thin omitted)

### Community 0 - "classify_sector"
Cohesion: 0.05
Nodes (55): apply(), classify_missing(), DailyQuotaExhausted, GeminiClassifier, load_cache(), Classify the works the keyword rules could not, using a language model. WHY…, The per-day free-tier allowance is gone. Unlike a per-minute rate limit this…, One sector per input, in order. Constraining the reply is what stops the model… (+47 more)

### Community 1 - "compliance_risk_score"
Cohesion: 0.40
Nodes (5): compliance_risk_score(), Most completed works genuinely have no recommendation date on record (see…, 29% of completed works have Has Images = False in the source data - a real…, test_missing_dates_flagged_only_for_recommended_works(), test_missing_photo_documentation_flagged_only_for_completed_works()

### Community 2 - "query"
Cohesion: 0.06
Nodes (61): execute(), _get_pool(), query(), Borrow a connection, run one statement, and hand it back. psycopg2's pool never…, Run a statement that writes, and commit it. Separate from query() rather than a…, _run(), agencies(), _alert_filters() (+53 more)

### Community 3 - "test_detectors.py"
Cohesion: 0.06
Nodes (60): benford_mad(), digit_shares(), _finding(), first_digit(), first_digit_anomaly(), fiscal_year(), idle_allocation(), mad_from_shares() (+52 more)

### Community 4 - "load_real_data.py"
Cohesion: 0.12
Nodes (16): check_headroom(), extract_fingerprint(), load(), loaded_fingerprint(), _newest(), _newest_optional(), prepare_insert_frame(), Load the real MPLADS CSV extracts into the `projects` table. Source: the four… (+8 more)

### Community 5 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (35): eslint, eslint-config-next, leaflet, react-dom, tailwindcss, @tailwindcss/postcss, @types/leaflet, @types/node (+27 more)

### Community 6 - "Vendor Concentration Tests"
Cohesion: 0.11
Nodes (33): _exp(), An agency's vendor mix in one Lok Sabha says nothing about the other. Pooling…, Snapshots predating ls_term hold one term; they must not fail the run., One big payment to one vendor is concentration even if fifty small payments go…, Two payments to one vendor is an HHI of 1.0 and means nothing., A snapshot with no expenditure file is supported; it must cost the signal, not…, test_concentration_risk_scales_between_floor_and_ceiling(), test_expenditures_without_a_term_column_still_profile() (+25 more)

### Community 7 - "Database Schema"
Cohesion: 0.11
Nodes (29): agency_vendor_profile, data_refresh, detector_findings, expenditures, idx_detector_findings_code, idx_detector_findings_severity, idx_detector_findings_subject, idx_expenditures_agency (+21 more)

### Community 9 - "build_sih_deck.py"
Cohesion: 0.13
Nodes (21): caption(), crore(), figures(), hotspot(), indian(), link_row(), main(), place() (+13 more)

### Community 10 - "api.ts"
Cohesion: 0.10
Nodes (19): STATUS_OPTION_LABELS, AgencyStat, AlertPage, ComplianceBook, ComplianceRule, DeskFinding, DeskSector, Detector (+11 more)

### Community 11 - "[state]/page.tsx"
Cohesion: 0.22
Nodes (7): next, Params, Search, StateDeskPage(), term(), StateDesk, nextConfig

### Community 12 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 13 - "format.ts"
Cohesion: 0.15
Nodes (17): react-leaflet, GeoJSON, MapContainer, MapPage(), TileLayer, RiskBar(), RiskComponents, STEPS (+9 more)

### Community 14 - "layout.tsx"
Cohesion: 0.15
Nodes (13): freshnessLine(), metadata, mono, navLinks, RootLayout(), sans, Cursor(), Logo() (+5 more)

### Community 15 - "MPLADS Risk Monitor — Design Spec (SIH26102)"
Cohesion: 0.09
Nodes (22): 10. Tech stack, 11. Explicitly cut from the original plan (2-day scope), 12. Error handling, 13. Testing, 14.1 Fixed in the snapshot that carries this addendum, 14.2 Confirmed at larger scale, no change needed, 14.3 Fixed — the cost baseline was measuring almost nothing, 14.4 Fixed — vendor concentration and payment ageing (+14 more)

### Community 16 - "test_load_real_data.py"
Cohesion: 0.24
Nodes (10): A work's identity is (Work ID, ls_term, IDA). The agency is part of the key,…, work_key(), Checks on work identity. Run: python data/test_load_real_data.py, Older snapshots hold one term only; the key still forms, with term 0., The nightly skips a rewrite when the extract fingerprints the same as what is…, Work IDs restart per implementing agency, not just per term. Two real rows from…, test_fingerprint_is_order_independent_and_value_sensitive(), test_work_key_is_stable_for_identical_input() (+2 more)

### Community 17 - "MoSPI Figure Verification"
Cohesion: 0.23
Nodes (11): aggregator(), main(), official(), ours(), post(), Persist the comparison so the interface can show it without calling the portal…, Reconcile our figures against the official MoSPI MPLADS dashboard. The problem…, �83,33,66,73,298.01' -> 83336673298.01 (+3 more)

### Community 18 - "formatCount"
Cohesion: 0.23
Nodes (17): AnalysisPage(), DistrictDeskPage(), Params, Search, MpPage(), ProjectsPage(), Pager(), RiskTicker() (+9 more)

### Community 19 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 20 - "MPLADS Data Fetcher"
Cohesion: 0.29
Nodes (10): main(), merge_terms(), open_export(), Merge logic survives quoted commas and embedded newlines. No network., Pull MPLADS export CSVs from api.empoweredindian.in for both Lok Sabha terms.…, GET one export as a streaming text handle. Retries on transient errors., Write one CSV combining every term, with ls_term as the last column., Every row has a known ls_term and the right field count. (+2 more)

### Community 21 - "test_current_refresh_run_id_ignores_an_abandoned_run"
Cohesion: 0.20
Nodes (4): current_refresh_run_id(), Find the 'running' data_refresh row load_real_data.py started, so this run's…, A run killed by a workflow timeout leaves its row at 'running' forever.…, test_current_refresh_run_id_ignores_an_abandoned_run()

### Community 22 - "scoring.py"
Cohesion: 0.18
Nodes (17): add_duplicate_features(), agency_risk_score(), compute_delay_days(), cost_risk_score(), delay_risk_score(), duplicate_risk_score(), load_was_skipped(), Cost risk from deviation above the peer median, 0 when peers are thin.… (+9 more)

### Community 23 - "_a_state"
Cohesion: 0.12
Nodes (16): _a_state(), A state that actually has works, taken from the data rather than named., The state desk and /api/states must never disagree about one state., The two rates are not interchangeable, and the desk labels one of them "Paid…, GET /api/trends?state=X returned 500 in production for as long as the parameter…, The header tiles took only min_score, so filtering the table to one district…, A detector finding must never be shown without its own limits. D-02 renders…, Reduce manual monitoring efforts" means the filtered list has to leave the… (+8 more)

### Community 24 - "Brag Plan: Kasauti"
Cohesion: 0.09
Nodes (21): Audio direction, Brag Plan: Kasauti, Duration: 24 seconds, Every figure in this video is real, Format: landscape — 1920x1080, Hook (first 2-3 seconds), Key moments (the middle), Outro / punchline (+13 more)

### Community 25 - "ProjectFilters"
Cohesion: 0.67
Nodes (3): ProjectFilters(), handleQChange(), updateParams()

### Community 26 - "Synthetic Data Generator"
Cohesion: 0.70
Nodes (3): build_dataset(), make_duplicate_pair(), make_project()

### Community 27 - "Vercel Deploy Config"
Cohesion: 0.50
Nodes (3): builds, routes, $schema

### Community 42 - "diagrams/package.json"
Cohesion: 0.14
Nodes (11): dependencies, playwright-core, description, name, private, type, BOARDS, DIR (+3 more)

### Community 45 - "_RecordingCursor"
Cohesion: 0.14
Nodes (6): fetch_projects(), Captures the SQL fetch_projects actually runs, and answers it minimally., A project with no work_key cannot be scored, because project_scores is keyed on…, _RecordingConn, _RecordingCursor, test_scoring_skips_rows_that_cannot_carry_a_score()

### Community 46 - "Kasauti — MPLADS verification"
Cohesion: 0.14
Nodes (13): 10. Interface, 11. Motion, measured, 1. Never claim more than the record supports, 2. `work_key` is the only identifier that survives a reload, 3. Source tables and derived tables are separate, and the swap is atomic, 4. Population statistics stay at population grain, 5. Thresholds are measured, not borrowed, 6. Money comes from the source's own aggregates (+5 more)

### Community 47 - "projects/[id]/page.tsx"
Cohesion: 0.23
Nodes (10): methodFor(), ProjectPage(), LABELS, ReviewTrail(), when(), ReviewHistory, hasPeers(), isNearDuplicate() (+2 more)

### Community 48 - "test_scoring.py"
Cohesion: 0.14
Nodes (18): build_flagged_reasons(), _priced(), A work can be a delay/spend outlier without being expensive. cost_risk blends…, A row with a complete cost basis: amount, peer median, peer count., A verifier who cannot see the basis cannot act on the flag., agency_risk is a max, so attributing it to the delay rate unconditionally…, A positional insert tuple fell one value short when `sector` was added to…, D-03 shipped silent for a whole scoring run because fetch_mps did not select… (+10 more)

### Community 49 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 50 - "add_base_features"
Cohesion: 0.22
Nodes (9): add_base_features(), The whole point of the fix. Two districts' worth of works, all with category…, A single Rs 7.5 crore work must not drag the baseline for its neighbours. With…, A median over three works is not a baseline., Scoring a database loaded before the sector column must not group every work in…, test_cost_baseline_groups_on_sector_not_category(), test_peer_median_resists_one_huge_work(), test_sector_is_recomputed_when_missing() (+1 more)

### Community 51 - "Data snapshot"
Cohesion: 0.25
Nodes (7): Data snapshot, Reconciliation against the source's own dashboard, Refreshing with newer data, Reproducing the full pipeline, Source, Why the earlier snapshot was half the data, Work IDs are not unique across terms

### Community 52 - "attach_agency_profile"
Cohesion: 0.29
Nodes (7): attach_agency_profile(), Left-join the per-agency-per-term vendor profile onto works. Keyed on…, Left join, not inner: no vendor data must cost the signal, not the rows., The same agency, two terms, two different vendor mixes. A work must be matched…, test_a_work_takes_its_own_terms_agency_profile(), test_attach_agency_profile_without_any_expenditure_data(), test_works_of_an_agency_with_no_expenditures_keep_scoring()

### Community 53 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 54 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 55 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 56 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 57 - "web/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 66 - "mp_key"
Cohesion: 0.19
Nodes (17): mp_key(), normalize_mp_name(), Stable identity for a Member of Parliament. WHY THIS EXISTS --------------- `MP…, Strip term marker and honorifics; casefold; collapse whitespace. Single…, Short stable id for one MP. Raises if the name normalises to nothing., mp_key, or None for a name that carries no usable text. Used on the works rows:…, safe_mp_key(), A work with an unusable MP name is still a work worth loading; it just cannot… (+9 more)

### Community 67 - "MPLADS Risk Monitor Implementation Plan"
Cohesion: 0.11
Nodes (18): Addendum — follow-up tasks from the 2026-08-31 data (Track: data), Global Constraints, MPLADS Risk Monitor Implementation Plan, Task 0: Postgres schema + repo scaffold + shared env contract, Task 10: Final integration / demo dry run (shared, last), Task 11: Derive a sector and fix the cost baseline — DONE, Task 12: Score vendor concentration at the agency grain — DONE, Task 13: Normalize MP identity — DONE (+10 more)

### Community 69 - "app/page.tsx"
Cohesion: 0.15
Nodes (14): react, COMPONENTS, LIMITS, MODELS, OverviewPage(), TERMS, metadata, ProvenancePage() (+6 more)

### Community 72 - "build_rows"
Cohesion: 0.33
Nodes (7): build_expenditure_rows(), build_rows(), parse_district(), District is the IDA prefix before the first '(' - e.g. 'CHITTOOR(DISTRICT…, Return (rows_df, rejects) where rejects is a list of (raw_row, reason, file)., Expenditure transactions, at their own grain. No join to works is attempted:…, to_date()

### Community 73 - "alerts/page.tsx"
Cohesion: 0.17
Nodes (15): ALLOWED, ReviewResult, submitReview(), AlertsPage(), reviewedLine(), STATUS_LABELS, DECISIONS, ReviewActions() (+7 more)

### Community 74 - "build.py"
Cohesion: 0.18
Nodes (9): at(), layout(), measure(), Emit the explainer composition, timed to the narration that was actually…, Seconds of audio in `path`, per ffprobe., Scene start/duration from the measured voice-over lengths., An absolute timeline position, `offset` seconds into a scene., A dense population and the few points sitting outside it. The first version… (+1 more)

### Community 75 - "Hyperframes Composition Brief: Kasauti"
Cohesion: 0.20
Nodes (9): Audio, Creative Direction, Hyperframes Composition Brief: Kasauti, Hyperframes Instructions, Objective, Output, Source Material, Storyboard (+1 more)

### Community 77 - "Kasauti — AI-powered MPLADS verification"
Cohesion: 0.20
Nodes (9): Kasauti — AI-powered MPLADS verification, Repository, Running it, The API, The deck, The interface, The nightly refresh, What it does (+1 more)

### Community 80 - "states/page.tsx"
Cohesion: 0.25
Nodes (7): band(), BAR_TONE, SortKey, SORTS, StatesPage(), get(), StateSummary

### Community 81 - "preview_deck.py"
Cohesion: 0.48
Nodes (6): colour(), inches(), main(), Render the built deck to PNGs so it can actually be looked at. There is no…, Emit one shape as a positioned div, recursing into groups., run_html()

### Community 82 - "The two-minute explainer"
Cohesion: 0.40
Nodes (4): Assets, How it is built, Rebuilding, The two-minute explainer

## Knowledge Gaps
- **251 isolated node(s):** `$schema`, `builds`, `routes`, `agency_vendor_profile`, `rejected_rows` (+246 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 524 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `normalize()` connect `classify_sector` to `mp_key`, `add_base_features`, `scoring.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `classify_sector()` connect `classify_sector` to `add_base_features`, `scoring.py`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Why does `add_base_features()` connect `add_base_features` to `classify_sector`, `test_scoring.py`, `scoring.py`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **What connects `$schema`, `builds`, `routes` to the rest of the system?**
  _251 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `classify_sector` be split into smaller, more focused modules?**
  _Cohesion score 0.050921861281826165 - nodes in this community are weakly interconnected._
- **Should `query` be split into smaller, more focused modules?**
  _Cohesion score 0.06299603174603174 - nodes in this community are weakly interconnected._
- **Should `test_detectors.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06345848757271286 - nodes in this community are weakly interconnected._