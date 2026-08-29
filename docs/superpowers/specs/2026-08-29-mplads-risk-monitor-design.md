# MPLADS Risk Monitor — Design Spec (SIH26102)

## 1. Problem & framing

AI-powered monitoring system for MPLADS (Member of Parliament Local Area
Development Scheme) project data. Detects suspicious patterns and
inefficiencies, assigns a risk score, and helps authorities prioritize
which projects need human verification.

**Explicit non-claim:** this system does not prove fraud. It flags
high-risk cases with evidence and a human-readable explanation, for a
human to verify.

## 2. Constraints

- Solo builder, 2 days, ~10 hrs/day (~20 hrs total), using 3 parallel
  Claude Code accounts/instances.
- No MPLADS/data.gov.in API access confirmed, nothing downloaded yet.
- Demo reliability for live SIH judging is the top priority — the
  architecture is chosen to minimize live-compute failure surface.

## 3. Data strategy

Hybrid: pull whatever real MPLADS sample data is quickly obtainable
(one state, or one downloadable report/CSV from data.gov.in/MPLADS
portal) for authenticity, and generate the bulk of the dataset
synthetically in the same schema to reach a demo-worthy scale
(target: low thousands of projects across multiple states/districts/
agencies, with a deliberately seeded set of anomalous cases — cost
outliers, delayed projects, near-duplicate descriptions, one
underperforming agency — so the risk engine has real things to catch).

If real data acquisition stalls past ~1-2 hours, fall back to 100%
synthetic without blocking the rest of the build.

## 4. Architecture

```
[Offline, one-time before demo]
MPLADS sample CSVs + synthetic generator
        |
        v
Python batch script (pandas)
   -> clean, compute features
   -> rules + Isolation Forest + sentence-transformers
   -> risk score + template-generated explanation
        |
        v
   PostgreSQL (final scored tables)

[Live, at demo time]
PostgreSQL -> FastAPI (read-only endpoints) -> Next.js dashboard
```

Nothing user-facing triggers live ML or LLM inference. All scoring
runs once, offline, before the demo. FastAPI and the frontend only
read already-scored rows. This is the core reliability decision: a
live-inference demo has failure modes (latency, flaky embedding calls,
LLM API errors) that a read-only demo does not.

## 5. Repo layout / parallel track split

Three tracks, one shared contract (Postgres schema + API response
shape) to agree up front so tracks can run in parallel across the 3
Claude accounts:

- `data/` (Track 1) — data acquisition, cleaning, feature
  calculation, batch scoring script. Owns the Postgres schema.
- `api/` (Track 2) — FastAPI, read-only endpoints over scored tables.
  Owns the API response shape.
- `web/` (Track 3) — Next.js + Tailwind dashboard, consumes the API.

## 6. Data model

`projects` table (raw + cleaned, one row per work):

```
id, work_name, description, mp_name, constituency,
state, district, category, implementing_agency,
recommended_amount, sanctioned_amount, expenditure,
work_status, start_date, expected_completion, actual_completion,
source (real | synthetic)
```

Columns added by the batch scoring script (same table — no separate
1:1 table, not worth the join given the time budget):

```
delay_days, cost_deviation_pct, expenditure_ratio,
district_avg_cost, agency_delay_rate, max_similarity_score,
similar_work_id

cost_risk, delay_risk, duplicate_risk, agency_risk, compliance_risk   (0-100 each)
overall_risk_score   (weighted sum: cost 25%, delay 25%, duplicate 20%,
                       agency 15%, compliance 15% — tunable constants,
                       not hardcoded inline)
risk_level            (LOW <40, MEDIUM 40-70, HIGH >70)
flagged_reasons        (jsonb array of short human-readable strings)
```

## 7. Risk scoring detail

- **Cost risk**: deviation of `sanctioned_amount` from the
  district+category average (Isolation Forest also runs across
  numeric features as a general-purpose catch-all for outliers rules
  don't anticipate).
- **Delay risk**: `delay_days` relative to category norms.
- **Duplicate risk**: sentence-transformers embeds `description`,
  cosine similarity checked within the same district+category;
  similarity >85% -> high duplicate_risk, `similar_work_id` stored so
  the UI can link the two projects.
- **Agency risk**: rolling delay rate and anomaly rate per
  `implementing_agency`.
- **Compliance risk**: straightforward rule checks (e.g. missing
  dates, expenditure > sanctioned amount, status inconsistent with
  dates).

`overall_risk_score` is a weighted sum of the five components (blended
with the Isolation Forest anomaly signal on the cost/delay side).
Weights live as named constants in the scoring script, not magic
numbers, so they're easy to retune after seeing real score
distributions.

## 8. Explanation generation

Template-generated from `flagged_reasons`, filled with the actual
computed numbers — e.g. "Cost is 41% above similar projects", "73 days
beyond expected completion", "91% similarity with another nearby
work". No live LLM call in the critical path. An LLM rephrase pass
into more natural prose is an optional polish step if time remains
near the end, never a dependency for the demo to function.

## 9. Dashboard (4 screens)

1. **National overview** — total projects, total expenditure,
   high-risk count, delayed count, anomaly count.
2. **Risk map** — state-level choropleth (India states geojson is
   readily available; no reliable free district-boundary geojson
   exists on short notice, so district-level is a filtered
   list/table, not a nested map).
3. **Project investigation** — single project: risk score, per-
   component risk breakdown, "why flagged" bullet list.
4. **Agency/district analysis** — aggregated stats per agency and per
   district (projects, delayed count, anomaly count, risk level).

## 10. Tech stack

| Layer | Technology |
|---|---|
| Data acquisition | Python (requests/pandas), manual download fallback |
| Database | PostgreSQL |
| Data processing / scoring | Pandas, Scikit-learn (Isolation Forest), Sentence Transformers |
| Backend | FastAPI, read-only |
| Frontend | Next.js + Tailwind CSS |
| Charts | Recharts |
| Map | Leaflet + public India states geojson |
| Deployment | Vercel (frontend + API) |

## 11. Explicitly cut from the original plan (2-day scope)

- Kafka / real-time ingestion pipeline — batch only.
- Live LLM explanation calls — template text; LLM rephrase is
  optional late-stage polish only.
- AWS deployment — Vercel only.
- District-level interactive map — state-level choropleth +
  filtered district table instead.
- Auth/login — none; open dashboard for the demo.

## 12. Error handling

- Batch script: per-row validation (missing amounts, malformed
  dates) — invalid rows go to a `rejected` log/table, never silently
  corrupt the scored data.
- API: no matching data returns an empty array with 200, not a 500.
- No other error-handling surface exists — nothing user-facing writes
  data during the demo.

## 13. Testing

- Batch scoring: one `test_scoring.py` with a handcrafted synthetic
  project of known delay/cost characteristics, asserting it lands in
  the expected risk band. Proves the scoring math isn't silently
  broken.
- API: smoke-check each endpoint returns 200 and the expected shape.
- Frontend: manual click-through of all 4 screens before calling the
  demo ready (per standard workflow — no automated UI test given the
  time budget).
