# Data snapshot

`mplads_2026-08-31.zip` (14.4 MB, 140 MB uncompressed) holds the full MPLADS
extract for **both Lok Sabha terms**:

- `mplads_completed_works_2026-08-31.csv` — 124,353 completed works
- `mplads_recommended_works_2026-08-31.csv` — 123,146 recommended works
- `mplads_expenditures_2026-08-31.csv` — 270,934 payment transactions
- `mplads_mp_summary_2026-08-31.csv` — 774 MPs × 2 terms

Every file carries an added `ls_term` column (17 or 18). The pipeline reads the
two work-level CSVs; the expenditure and MP-summary files ship alongside them
for vendor- and MP-level analysis that does not exist yet.

`mplads_2026-08-30.zip` (4.4 MB) is the previous snapshot, kept because the
reconciliation figures below were measured against it. It holds only the 18th
Lok Sabha — see "Why the earlier snapshot was half the data".

Committed so the pipeline is reproducible from a clone alone: no external
hosting, no credentials beyond a database URL.

## Reconciliation against the source's own dashboard

Checked 2026-09-09 for the 18th Lok Sabha, the view empoweredindian.in opens on:

| metric | ours | theirs |
|---|---|---|
| Total MPs | 774 | 774 |
| Total allocated | Rs 11,681.9 Cr | Rs 11,681.9 Cr |
| Vendor expenditure | Rs 3,964.3 Cr | Rs 3,995.3 Cr |
| Fund utilisation | 66.5% | 67.7% |
| Completed works | 43,650 | 44,028 |

Every figure sat *below* theirs, never above, which is what a stale snapshot
looks like rather than a broken pipeline - a mangled load misses in both
directions. Allocation matched to the decimal, and allocation is the figure
that would break first if anything were wrong. The 2026-09-09 fetch closed the
gap: it returns exactly 44,028 completed works for the 18th term.

Three different money figures live in this data and they are not
interchangeable. Reporting the wrong one under a label implying it matched the
source is what made ours look wrong while being right:

- **completed works value** - what finished works finally cost. Reconciles
  with the source's published `completedWorksValue`.
- **sanctioned total** - what has been sanctioned, finished or not.
- **vendor payments** - what the expenditure extract records being paid out.
  This is what the source's dashboard calls "Total Expenditure".

And scope matters as much as metric: the source's dashboard defaults to one
term, so pooling both made our totals roughly double theirs. /api/overview
takes an ls_term, and the overview page defaults to the 18th for that reason.

## Source

MPLADS programme data, obtained via [Empowered Indian](https://empoweredindian.in),
which aggregates the official MoSPI MPLADS portal. MPLADS records are public
government data.

`scripts/fetch_mplads.py` reproduces these files from their public API. It has
no dependencies beyond the standard library:

```bash
python3 scripts/fetch_mplads.py               # all four, skips existing
python3 scripts/fetch_mplads.py --self-check  # offline, tests the merge logic
```

Against the 2026-08-30 snapshot, our loaded total (₹23,821,967,508.61)
reconciles with the published `completedWorksValue` of ₹23,869,325,463.61: the
difference of ₹47,357,955.00 is exactly the 85 completed works rejected for
having no work description, which cannot participate in duplicate detection.

## Why the earlier snapshot was half the data

The API's export endpoints default to `ls_term=18` when the parameter is
omitted. The 2026-08-30 snapshot was pulled without it, so it captured the 18th
Lok Sabha alone:

```
/api/export/completed-works                 -> 43,735
/api/export/completed-works?ls_term=18      -> 43,735
/api/export/completed-works?ls_term=17      -> 80,618
```

`scripts/fetch_mplads.py` always requests 17 and 18 explicitly and merges them,
which is what makes this snapshot 2.8× the size of the last one.

## Work IDs are not unique across terms

Work IDs restart per term: 9,862 completed Work IDs appear in both extracts as
different works. `load_real_data.py` therefore keys a work on
`(Work ID, ls_term)`. Matching on Work ID alone finds 804 shared IDs between the
recommended and completed files, of which only 611 are real — the other 193 are
unrelated works that happen to share a number across terms, and would silently
take each other's start date.

Snapshots taken before the `ls_term` column existed hold one term only, so the
loader treats a missing column as a single term. Verified: the 2026-08-30
snapshot still resolves the same 440 shared works it always did.

## Reproducing the full pipeline

```bash
unzip data/snapshot/mplads_2026-08-31.zip -d mplads-data
export MPLADS_DATA_DIR=mplads-data
export DATABASE_URL='postgres://...'

python -m venv data/.venv && source data/.venv/bin/activate
pip install -r data/requirements.txt

psql "$DATABASE_URL" -f data/schema.sql
python data/load_real_data.py # ~2 min, loads 246,487 rows, rejects 401
python data/scoring.py        # ~30-40 min (embeds 246k descriptions)
```

The loader resolves the newest `mplads_<kind>_*.csv` in `MPLADS_DATA_DIR`, so
dropping in a later snapshot works without code changes.

**Scoring time roughly doubled with this snapshot** (127k descriptions to 246k).
The nightly workflow's `timeout-minutes: 60` still covers it, but the margin is
now thin — if that job starts timing out, that is why. The largest
`(district, category)` similarity group is 3,293 works (JAUNPUR), a 10.8M-cell
matrix, so memory is not the constraint; embedding throughput is.

## Refreshing with newer data

Re-run `scripts/fetch_mplads.py`, zip the four CSVs using the same filename
convention (`mplads_<kind>_YYYY-MM-DD.csv`), and drop the zip in here — the
nightly workflow takes the lexically-last zip, and the loader takes the
lexically-last CSV of each kind. To pull from a live source instead, set the
`MPLADS_DATA_URL` repository secret to a URL serving an equivalent zip; the
workflow prefers it over this committed snapshot.
