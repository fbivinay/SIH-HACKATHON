# Graph Report - SIH HACKATHON  (2026-09-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 700 nodes · 1242 edges · 45 communities (27 shown, 17 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.85)
- Token cost: 37,906 input · 601 output

## Graph Freshness
- Built from commit: `eaf643ff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- LLM Sector Classification
- Risk Scoring Engine
- Database & API Layer
- Anomaly Detectors
- Data Loading Pipeline
- Frontend Dependencies
- Vendor Concentration Tests
- Database Schema
- SIH Deck Generator
- API Types & Review Trail
- District, MP & Project Pages
- TypeScript Config
- Map & Analysis Pages
- Layout & Navigation
- Compliance & Signals Pages
- Review Submission Actions
- MoSPI Figure Verification
- Alerts & Project Filters
- State Desk Page
- MPLADS Data Fetcher
- Refresh Run Tracking
- States Listing Page
- State/District Desk Tests
- Overview Page
- Risk Bar Component
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
- Provenance Gap Test
- Quiet Agency Detector Test
- MP Dashboard Scoping Test
- Review Token Fail-Closed Test
- Screenshot Script
- ESLint Config
- PostCSS Config

## God Nodes (most connected - your core abstractions)
1. `formatCount()` - 35 edges
2. `query()` - 32 edges
3. `formatINR()` - 23 edges
4. `riskLevelLabel()` - 18 edges
5. `api` - 17 edges
6. `classify_sector()` - 16 edges
7. `riskLevelClass()` - 16 edges
8. `compilerOptions` - 16 edges
9. `normalize()` - 15 edges
10. `idle_allocation()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `classify_sector()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `main()` --calls--> `normalize()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `unclassified_descriptions()` --calls--> `normalize()`  [INFERRED]
  scripts/classify_sectors.py → data/sectors.py
- `set_review()` --references--> `post()`  [EXTRACTED]
  api/main.py → scripts/verify_mospi.py
- `add_base_features()` --indirect_call--> `classify_sector()`  [INFERRED]
  data/scoring.py → data/sectors.py

## Import Cycles
- None detected.

## Communities (45 total, 17 thin omitted)

### Community 0 - "LLM Sector Classification"
Cohesion: 0.05
Nodes (55): apply(), classify_missing(), DailyQuotaExhausted, GeminiClassifier, load_cache(), Classify the works the keyword rules could not, using a language model. WHY…, The per-day free-tier allowance is gone. Unlike a per-minute rate limit this…, One sector per input, in order. Constraining the reply is what stops the model… (+47 more)

### Community 1 - "Risk Scoring Engine"
Cohesion: 0.06
Nodes (60): add_base_features(), add_duplicate_features(), agency_risk_score(), attach_agency_profile(), build_flagged_reasons(), compliance_risk_score(), compute_delay_days(), cost_risk_score() (+52 more)

### Community 2 - "Database & API Layer"
Cohesion: 0.07
Nodes (57): execute(), _get_pool(), query(), Borrow a connection, run one statement, and hand it back. psycopg2's pool never…, Run a statement that writes, and commit it. Separate from query() rather than a…, _run(), agencies(), _alert_filters() (+49 more)

### Community 3 - "Anomaly Detectors"
Cohesion: 0.07
Nodes (55): benford_mad(), digit_shares(), _finding(), first_digit(), first_digit_anomaly(), fiscal_year(), idle_allocation(), mad_from_shares() (+47 more)

### Community 4 - "Data Loading Pipeline"
Cohesion: 0.06
Nodes (44): build_expenditure_rows(), build_mp_rows(), build_rows(), load(), _newest(), _newest_optional(), parse_district(), prepare_insert_frame() (+36 more)

### Community 5 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (35): eslint, eslint-config-next, leaflet, react-dom, tailwindcss, @tailwindcss/postcss, @types/leaflet, @types/node (+27 more)

### Community 6 - "Vendor Concentration Tests"
Cohesion: 0.11
Nodes (33): _exp(), An agency's vendor mix in one Lok Sabha says nothing about the other. Pooling…, Snapshots predating ls_term hold one term; they must not fail the run., One big payment to one vendor is concentration even if fifty small payments go…, Two payments to one vendor is an HHI of 1.0 and means nothing., A snapshot with no expenditure file is supported; it must cost the signal, not…, test_concentration_risk_scales_between_floor_and_ceiling(), test_expenditures_without_a_term_column_still_profile() (+25 more)

### Community 7 - "Database Schema"
Cohesion: 0.11
Nodes (29): agency_vendor_profile, data_refresh, detector_findings, expenditures, idx_detector_findings_code, idx_detector_findings_severity, idx_detector_findings_subject, idx_expenditures_agency (+21 more)

### Community 9 - "SIH Deck Generator"
Cohesion: 0.16
Nodes (20): card(), chip(), crore(), figures(), fit_h(), main(), n(), _pointer_text() (+12 more)

### Community 10 - "API Types & Review Trail"
Cohesion: 0.10
Nodes (19): LABELS, ReviewTrail(), when(), AgencyStat, AlertPage, ComplianceBook, DeskFinding, DeskSector (+11 more)

### Community 11 - "District, MP & Project Pages"
Cohesion: 0.25
Nodes (13): DistrictDeskPage(), Params, Search, MpPage(), ProjectPage(), ProjectsPage(), DistrictDesk, formatINR() (+5 more)

### Community 12 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 13 - "Map & Analysis Pages"
Cohesion: 0.22
Nodes (14): react-leaflet, AnalysisPage(), GeoJSON, MapContainer, MapPage(), TileLayer, CHOROPLETH_STEPS, choroplethFill() (+6 more)

### Community 14 - "Layout & Navigation"
Cohesion: 0.15
Nodes (13): freshnessLine(), metadata, mono, navLinks, RootLayout(), sans, metadata, ProvenancePage() (+5 more)

### Community 15 - "Compliance & Signals Pages"
Cohesion: 0.21
Nodes (13): CompliancePage(), STATUS, evidenceLine(), severityClass(), SignalsPage(), metadata, MonthlyBars(), TrendsPage() (+5 more)

### Community 16 - "Review Submission Actions"
Cohesion: 0.24
Nodes (10): react, ALLOWED, ReviewResult, submitReview(), DECISIONS, ReviewActions(), REVIEWER_STORAGE_KEY, ReviewerName() (+2 more)

### Community 17 - "MoSPI Figure Verification"
Cohesion: 0.23
Nodes (11): aggregator(), main(), official(), ours(), post(), Persist the comparison so the interface can show it without calling the portal…, Reconcile our figures against the official MoSPI MPLADS dashboard. The problem…, �83,33,66,73,298.01' -> 83336673298.01 (+3 more)

### Community 18 - "Alerts & Project Filters"
Cohesion: 0.19
Nodes (10): AlertsPage(), reviewedLine(), STATUS_LABELS, ProjectFilters(), handleQChange(), updateParams(), STATUS_OPTION_LABELS, Alert (+2 more)

### Community 19 - "State Desk Page"
Cohesion: 0.22
Nodes (7): next, Params, Search, StateDeskPage(), term(), StateDesk, nextConfig

### Community 20 - "MPLADS Data Fetcher"
Cohesion: 0.29
Nodes (10): main(), merge_terms(), open_export(), Merge logic survives quoted commas and embedded newlines. No network., Pull MPLADS export CSVs from api.empoweredindian.in for both Lok Sabha terms.…, GET one export as a streaming text handle. Retries on transient errors., Write one CSV combining every term, with ls_term as the last column., Every row has a known ls_term and the right field count. (+2 more)

### Community 21 - "Refresh Run Tracking"
Cohesion: 0.20
Nodes (4): current_refresh_run_id(), Find the 'running' data_refresh row load_real_data.py started, so this run's…, A run killed by a workflow timeout leaves its row at 'running' forever.…, test_current_refresh_run_id_ignores_an_abandoned_run()

### Community 22 - "States Listing Page"
Cohesion: 0.25
Nodes (7): band(), BAR_TONE, SortKey, SORTS, StatesPage(), get(), StateSummary

### Community 23 - "State/District Desk Tests"
Cohesion: 0.25
Nodes (8): _a_state(), A state that actually has works, taken from the data rather than named., The scope guard. The rollup and the per-district rows are separate queries; if…, The state desk and /api/states must never disagree about one state., test_district_desk_404_for_an_unknown_district(), test_district_desk_agrees_with_its_parent_state_row(), test_state_desk_money_matches_the_state_list(), test_state_desk_totals_agree_with_its_own_district_table()

### Community 24 - "Overview Page"
Cohesion: 0.33
Nodes (5): COMPONENTS, LIMITS, OverviewPage(), TERMS, Overview

### Community 25 - "Risk Bar Component"
Cohesion: 0.40
Nodes (5): RiskBar(), RiskComponents, STEPS, WEIGHTS, riskScoreColorHex()

### Community 26 - "Synthetic Data Generator"
Cohesion: 0.70
Nodes (3): build_dataset(), make_duplicate_pair(), make_project()

### Community 27 - "Vercel Deploy Config"
Cohesion: 0.50
Nodes (3): builds, routes, $schema

## Knowledge Gaps
- **101 isolated node(s):** `AgencyStat`, `AlertPage`, `ComplianceBook`, `DeskFinding`, `DeskSector` (+96 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 304 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `normalize()` connect `LLM Sector Classification` to `Risk Scoring Engine`, `Data Loading Pipeline`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `classify_sector()` connect `LLM Sector Classification` to `Risk Scoring Engine`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Why does `next` connect `State Desk Page` to `District, MP & Project Pages`, `Frontend Dependencies`, `Layout & Navigation`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `AgencyStat`, `AlertPage`, `ComplianceBook` to the rest of the system?**
  _101 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `LLM Sector Classification` be split into smaller, more focused modules?**
  _Cohesion score 0.0504828797190518 - nodes in this community are weakly interconnected._
- **Should `Risk Scoring Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.05721153846153846 - nodes in this community are weakly interconnected._
- **Should `Database & API Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.06721215663354763 - nodes in this community are weakly interconnected._